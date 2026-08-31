# ---------- closing state (G-21) ----------
#
# CLOSING is a STATE, not a role: from the moment a seat's own `checkout --renew` arms its
# renewal, it has exactly one job left — write its handoff, go. Every other message arriving in
# that window is work it will never do and context the handoff needs. G-20 bounds WHO a seat is;
# G-21 bounds WHEN. Inbox while closing: the seat's OWN mute plus `leader`, nothing else. (The
# `closer-*` seat this state was originally cut for `close <seat>` spawning is deleted [T2-R9] —
# `entry["closer"]` below now always names the closing seat itself.)
#
# Kept in its own file rather than a roster column: workers.md's row grammar is frozen (WORKER_ROW
# / row_text) and every reader parses it positionally, so widening it to carry a flag that lives
# for minutes would be the expensive way to store the cheap thing.

def closing_path(base):
    return base / "closing.json"


def load_closing(base):
    """{seat: {"since": ts, "closer": name}} for every seat currently being closed. Never fatal:
    an unreadable or malformed file means "nobody is closing" — the fail-safe direction, since a
    parse error must not silence the room."""
    path = closing_path(base)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def closing_age_min(entry):
    """Minutes since the close began, or None when the stamp is unreadable."""
    try:
        return max(0, int((datetime.now()
                           - datetime.strptime((entry or {}).get("since", "").strip(),
                                               "%Y-%m-%d %H:%M")).total_seconds() // 60))
    except (ValueError, AttributeError, TypeError):
        return None


def closing_entry(base, seat):
    """`seat`'s closing state, or None — EXPIRED entries read as None.

    The expiry is not tidiness, it is the failure this run already had: a closer can DIE mid-close
    (G-11 killed one outright, and three seats were SIGKILLed tonight). Without an expiry, a dead
    closer would leave its target narrowed for the rest of the run — cut off from the room with no
    remedy anyone would think to look for. A close ceremony takes minutes; past CLOSING_MAX_MIN the
    state is assumed orphaned and the seat is treated as ordinary again. Fail-safe direction: an
    unreadable stamp expires too, because a seat wrongly narrowed goes quiet where a seat wrongly
    left open merely reads a message it did not need."""
    entry = load_closing(base).get(seat)
    if entry is None:
        return None
    age = closing_age_min(entry)
    if age is None or age > CLOSING_MAX_MIN:
        return None
    return entry


def closing_seats(base):
    return {seat for seat in load_closing(base) if closing_entry(base, seat) is not None}


# ---- G-134: the AWAITING-CLOSE debt ----------------------------------------------------------
# A seat can complete its OWN lifecycle (`checkout` — its last act per protocol §8) but only the
# leader can free its resources (`close-seat`, which kills the pane and verifies the harness pids
# are gone). Nothing bounded, drove, or even NOTICED the interval between the two: a seat read
# `active: no` on the roster while its pane held RAM against a 2800 MB launch floor, until a human
# happened to look. One instance ran 41 minutes and was found by hand.
#
# THE DEFECT WAS NEVER A MISSING KILL, and the refusal that stood here is now SATISFIED rather than
# reversed. The stated fix — have `checkout` kill its own pane — was refused because the in-place
# renew path needs the pane alive at close time (G-12), that path is CONDITIONAL (G-154: taken only
# when the seat already sits in the window its briefing asks for), and "at checkout time nothing
# knows which case a later renew will be." Both halves are now answered, neither by loosening it:
#   1. THE CASE IS KNOWN, because the DISPOSITION arrives WITH the checkout
#      (`checkout --renew --handoff "…"` vs a plain done-checkout) and is ASSERTED onto the record
#      below rather than inferred later. Checkout no longer leaves the renewal question open; it
#      carries the answer.
#   2. THE PANE IS STILL NOT KILLED BY THE CALLER — nothing in `cmd_checkout` kills anything. On
#      the RENEW disposition the caller forks a DETACHED executor (`lifecycle-exec`, built to
#      `arm_pid_reaper`'s form) and exits. The pane stays alive until the EXECUTOR — out-of-pane,
#      outliving its caller — makes the G-154 decision itself, calling `renew_in_place` with the
#      pane's window measured live. In-place respawn keeps the pane; re-place kills it. The
#      condition is evaluated where it CAN be evaluated, which is the one thing checkout could
#      never do.
# THE PANE of a persistent done-checkout is still not killed here: it lives until leader runs
# `close-seat`, which is where the relay-door refusal gets its say before the viewport dies — a seat
# carrying `relays:` to a human role is refused there unless the caller passes `--force`, because a
# door in the wrong place is cosmetic and a door destroyed is an outage. The HARNESS PROCESS is
# another matter: leaving it idle after a declared ending was the 2d11h leak (G-leader-0823-0217-2).
# The non-renew path arms `arm_pid_reaper` for every seat, not only `ephemeral: yes`.
# So W1 is respected, not worked around: on this path no process respawns the pane it runs in — the
# act that respawns runs OUTSIDE it, which is why `cmd_close_seat`'s self-act W1 warning is still
# printed for the caller who reaches the respawn from inside its own pane.
# `depart` remains the wrong precedent, for its own reason — a seat leaving for good, with no
# renewal question to answer. What changed is not the wall; it is that the answer now arrives
# BEFORE the wall instead of after it.
#
# So the record is written, not the kill: checkout ASSERTS the debt (who, which pane, whether the
# transcript landed, when), and close-seat/depart clear it. That makes #259's ratified hand-mapping
# — roster-done + pane-alive + transcript-EXISTS -> kill by pane id — a fact the tool WROTE rather
# than a state a later pass RECONSTRUCTS from roster + tmux + filesystem. This run has catalogued
# six instances of inferring a property from ambient context (G-101, G-107, G-121, G-124, G-128,
# and the engineer's own circular origin); a reaper that re-derives the debt each pass would be the
# seventh. An assertion at the moment of truth beats an inference at the moment of action.
#
# ⚠ THIS STATE DELIBERATELY DOES NOT EXPIRE, and that is the one place it must NOT copy `closing`
# above. There, expiry is fail-safe: a dead closer would otherwise leave its target narrowed and
# silent forever, so forgetting is the safer error. Here the entry IS the leak report — an expiry
# would delete the evidence of a pane still holding memory and restore exactly the silence this
# exists to end. A debt that ages out unpaid is not a debt.

def undelivered_flags(base):
    """[(stamp, text)] for every monitor flag the messaging layer REFUSED, newest last.

    Written by watch.py as a plain append, deliberately outside the message log: it reports that
    the messaging layer refused something, so routing it back through that layer is the one path
    guaranteed to fail the same way. Surfaced by `status` and `workers` because a monitor that
    cannot deliver must SHOUT that it cannot deliver — tonight's context warnings were computed
    correctly, refused correctly, printed to a detached stderr file, and lost, while the loop went
    on reporting healthy. Silence and health were indistinguishable at exactly the wrong place."""
    path = base / "undelivered-flags.md"
    if not path.exists():
        return []
    try:
        out = []
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if ln.startswith("- ") and "|" in ln:
                stamp, _, rest = ln[2:].partition("|")
                out.append((stamp.strip(), rest.strip()))
        return out
    except OSError:
        return []


def undelivered_line(base):
    """One line for the roster/status views, or '' when nothing was ever refused."""
    flags = undelivered_flags(base)
    if not flags:
        return ""
    return (f"UNDELIVERED MONITOR FLAGS: {len(flags)} — the watch loop computed a warning and the "
            f"messaging layer refused it. Most recent: {flags[-1][0]} {flags[-1][1][:110]}\n"
            f"  Read them all: {base / 'undelivered-flags.md'}")


def posted_open_asks_for_seat(args, seat):
    """Posted open asks this seat still owes an owner answer — empty if the store cannot be read.

    Fail-open on an unreadable store: this is the park detector for `--renew` refusal and for
    stamping `blocked-on-human`, not the D8 done-hold (that one fail-closes). A missing store must
    not strand an ordinary context-refresh."""
    try:
        return list(ending_store.list_open_asks(package_dir(args), seat=seat, posted=1) or [])
    except ending_store.EndingStoreError:
        return []


def stamp_checkout_ending(args, seat, kind, *, declared=None, diagnostic="", evidence="",
                          park_on_owner=False):
    """Seat-declare / system rewrite for one checkout (spec §4.1 cell map).

    ⚠ THE DECLARED OUTPUTS ARE RESOLVED THROUGH `output_candidates`, THE PRESENCE CHECK'S OWN
    RULE. The store re-runs a mechanical output check against the paths it is handed (§1.3), so a
    pointer resolved by any other rule makes it grade a different file from the one the kit just
    graded — which is what `{package}/workers/{seat}` did to every `seats/`-layout package. The
    candidate that EXISTS is stamped where there is one, and the check's own first candidate
    otherwise, so a genuinely missing output still names the path the author meant."""
    pkg = package_dir(args, register=False)
    _w = next((x for x in launch.discover_workers(workers_dir(args)) if x["agent"] == seat), None)
    abs_decl = []
    for p in declared or []:
        if is_output_template(p):
            continue
        pp = Path(p)
        if pp.is_absolute():
            abs_decl.append(str(pp))
            continue
        if _w is None:                       # no descriptor to resolve against — say so plainly
            abs_decl.append(str((pkg / p).resolve()))
            continue
        _cands = output_candidates(_w, p, str(Path(_w["cwd"]) / p))
        _hit = next((c for c in _cands
                     if c.is_dir() or (c.is_file() and c.stat().st_size > 0)), _cands[0])
        abs_decl.append(str(_hit))
    ev = evidence or (abs_decl[0] if abs_decl else f"checkout:{seat}")
    if kind == "done":
        return ending_store.stamp_seat_declare(
            pkg, seat, "done", declared_outputs=abs_decl, evidence=ev)
    if kind == "incomplete":
        # A seat may not stamp incomplete disarmed (writers.js). Owner-wait is a fact the KIT
        # witnessed (posted open asks), so the park is system-voice `blocked-on-human` — armed=0
        # until `ask-answered`. Tasks 41+159: this is the one parked-wait ending; `--renew` is
        # refused on the same fact, never delayed.
        if park_on_owner:
            return ending_store.stamp_system(
                pkg, seat, "incomplete", diagnostic="blocked-on-human",
                armed=0, named_event="ask-answered", evidence=ev)
        return ending_store.stamp_seat_declare(
            pkg, seat, "incomplete", diagnostic=diagnostic or "context full", evidence=ev)
    if kind == "outputs-missing":
        return ending_store.stamp_system(
            pkg, seat, "failed", reason_class="outputs-missing",
            diagnostic="outputs-missing", evidence=ev)
    raise ValueError(f"unknown checkout stamp {kind!r}")


def awaiting_debts(base, live=None):
    """[(seat, entry, age_min, alive)] oldest first — the reap debt, ready to render or to reap.

    ⚠ THE DEBT IS THE SUPERVISOR'S, AND ITS LIVENESS IS THE REGISTRY'S [T4-R8, C-15]. Both halves
    moved. The debt used to be read out of `awaiting-close.json`; that file went away with
    spec-state-store §4.1's second ending writer, so `load_awaiting` has answered a permanent `{}`
    ever since and this function could never report anything — a reaper that can never find a debt
    leak-guards nothing (G-134). The successor fact needs no second store and is derived, not kept:
    a supervisor registry row STILL PRESENT while its sitting already carries an ending is, by
    registry write moment (iii), a reap that did not complete.

    And `alive` is now the registry probe (pid + /proc start-time), not `pane in live_panes()`. The
    two answers differ exactly where it matters: a pane outlives its harness, so a pane-alive debt
    was routinely reported as "still holding memory" when the process was long gone, and a
    paneless daemon-lane sitting could never be reported as holding anything at all.

    `live` is accepted and IGNORED — kept so the roster's single `live_panes()` read still threads
    through unchanged. The pane set is a viewport enumeration and was never an answer here."""
    del live  # a viewport set is not a liveness input [T4-R8]
    pkg = base.parent if getattr(base, "name", "") == "coordination" else base
    try:
        rows = supervisor_door.awaiting_reap(pkg)
    except (supervisor_door.SupervisorError, OSError, ValueError):
        return []   # a probe that cannot run reports no debt; it never invents one
    out = []
    for row in rows or []:
        seat = row.get("seat")
        if not seat:
            continue
        entry = {"pane": row.get("pane") or "", "since": row.get("since") or "",
                 "pid": row.get("pid"), "exported": row.get("exported", False)}
        out.append((seat, entry, closing_age_min(entry), bool(row.get("alive"))))
    return sorted(out, key=lambda r: (-1 if r[2] is None else r[2]), reverse=True)


# ── `reap_blockers` AND `confirm_reap` ARE BOTH DELETED HERE, NOT DISABLED ────────────────────
#
# `confirm_reap` — the two-pass reap ledger — went first: it had no caller left and could not have
# run if it had one, because its last act wrote `awaiting_path(base)`, a function that went away
# with the debt file itself, so any call would have raised NameError inside a lock.
#
# `reap_blockers` — the pane-reap precondition list — follows it, and for a stronger reason than
# "no caller". Its whole SUBJECT is gone. It answered "may this PANE be killed to free memory",
# and [T4-R8] deletes the pane as a liveness surface: a pane is a viewport, not a heartbeat. The
# reap that survives is `supervisor.confirmAndReap`, which is keyed on a `(goal, seat)` REGISTRY
# ROW and a `kill(pid,0)` + `/proc` start-time probe, signals the PROCESS, and waits for it to
# actually go [spec-supervisor §4]. `cmd_reap` has routed through it since the debt file died;
# nothing has called this function in between, so it has been dead code with a live-looking
# selftest block in front of it — the shape that makes a suite report coverage it does not have.
#
# ⚠⚠ TWO THINGS THIS FUNCTION CARRIED HAVE NO SUCCESSOR ON THE NEW PATH, and they are recorded
# here rather than lost quietly, because both were owner-level rulings and neither is re-derivable
# from the code that replaces this:
#
#   1. THE HUMAN-DOOR EXEMPTION (`r-owner-afk-liaison-parked`, owner-ruled via leader #341). A seat
#      whose descriptor declares `relays:` carries the path to a human role, so its pane is a DOOR
#      and was never reapable. `supervisor/death-stamp.js#confirmAndReap` has no counterpart — its
#      own build memory says so (`20260824-c-supervisor-death-stamp`, ATTENTION 4): a `done`
#      checkout now reaps EVERY seat. A parked owner door that ends its sitting will be terminated.
#   2. #259's TRANSCRIPT PRECONDITION and its `d-transcript-consumers-split` precedence
#      (harness-native export FIRST, pipe-pane `recorded` log as the fallback, empty counting as
#      missing). The reap no longer gates on a transcript existing at all; what the store requires
#      instead is an `evidence_pointer` on the ending itself [§1.2], which is a different and
#      weaker guarantee — it names evidence, it does not verify the file is on disk and non-empty.
#
# Both belong to the supervisor seat, not to this file, and are filed as owed work rather than
# reconstructed here on the retired surface.


def set_closing(base, seat, closer):
    """Mark `seat` as closing -> `(ok, detail)`. Best-effort like every other coordination
    side-effect: a failure to write must never abort a close that has already spawned its closer.

    7.102 (s12-09): THE BOUNDARY'S OWN REASON TRAVELS WITH THE VERDICT. This returned a bare
    False, so the reason died here and `checkout_renew_arm`'s WARNING could only say the mute
    could not be written — leaving a seat unable to tell a harness-classifier DENIAL from a FULL
    DISK, two failures needing opposite responses. `detail` is "" on success and carries the
    exception's own text on failure; the caller prints it verbatim rather than re-deriving it.
    """
    try:
        with coord_lock(base):
            data = load_closing(base)
            data[seat] = {"since": now(), "closer": closer}
            atomic_write(closing_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True, ""
    except (OSError, ValueError) as e:
        return False, f"{type(e).__name__}: {e}"


def clear_closing(base, seat):
    """Drop `seat`'s closing state — the state dies WITH the close (or with a renew: the successor
    is a fresh seat with a full inbox). Returns True when a state was actually cleared."""
    try:
        with coord_lock(base):
            data = load_closing(base)
            if seat not in data:
                return False
            del data[seat]
            atomic_write(closing_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError):
        return False


def permitted_senders(agent, decls, roster):
    """Who may write to `agent` — or None when its inbox is unbounded. G-197.

    ⚠ `roster` IS A SEPARATE ARGUMENT AND MUST NOT BE `decls`. `inbox_decls` keeps a seat only
    when that seat DECLARES something (`if d: decls[agent] = d`), so an ordinary seat — the leader
    included — is ABSENT from it. Deriving the candidates from `decls` therefore skipped every
    plain seat and reported them as unreachable. Measured, and not by the suite: the first live
    render told this seat that `leader`, which had been messaging it all session, "NO seat
    declares". The fixture had listed `leader: {}` explicitly and so could never produce the bug —
    a fixture shaped to dodge the real path.

    ⚠ THE ANSWER IS EVALUATED, NEVER RE-DERIVED. Every candidate is run through
    `sender_admitted` — the SAME predicate `send` enforces and `why_not_woken` reports — against a
    probe message. Spelling the rule a second time here would produce two computations of "may X
    write to me" that agree today and drift apart on the next bound; this run has already paid for
    that twice (the wake set vs the read set, and the five hand-derived copies of
    `sender != me AND addressed_to`).

    `origin: ""` in the probe is the LOCAL case, deliberately: the question is who may write from
    inside this package. A foreign sender is refused by `sender_admitted`'s own origin test, and
    asserting that here would be the second copy this docstring exists to prevent.

    Returns (literal, relayed, dead_tokens): seats admitted by name, (seat, token) pairs admitted
    by relay, and bound tokens that resolve to NOBODY — the last because a bound naming a token no
    seat carries makes the seat unreachable by that name, silently. That is not hypothetical: it is
    what `senders: leader, master` did before `relays:` existed.
    """
    bound = ((decls or {}).get(agent) or {}).get("senders")
    if bound is None:
        return None
    literal, relayed, live = [], [], set()
    for cand in sorted(set(roster) | set(decls)):
        if cand == agent or not sender_admitted({"sender": cand, "origin": ""}, bound, decls):
            continue
        live.add(cand)
        if cand in bound:
            literal.append(cand)
        else:
            relayed.extend((cand, tok) for tok in sorted(bound)
                           if cand in relay_seats(tok, decls))
    dead = sorted(tok for tok in bound
                  if tok not in live and not relay_seats(tok, decls))
    return literal, relayed, dead


def inbox_bound_line(agent, decls, roster):
    """One line telling a bounded seat WHO may write to it, or '' when unbounded. G-197.

    ⚠ CALLER-ONLY BY CONSTRUCTION, and this is the acceptance bar rather than a nicety: the single
    call site passes the identity the CLI resolved for the caller, and there is no argument here
    that lets a seat ask about another. A command that answered for any seat would hand every seat
    a roster-wide map of who may talk to whom — a strictly larger disclosure than the foreign
    descriptor read this exists to make unnecessary.

    The defect it closes: a bounded seat could not learn its own bound from the tool at all. The
    kit RESOLVES `senders:`/`relays:` on every send and reports the refusal to the SENDER — while
    the bounded seat's own `inbox:` line described only broadcast scope, and said "direct messages
    always reach you", which for a bounded seat IS FALSE. Verifying the bound therefore meant
    reading another seat's descriptor: the tool knew the answer and offered no way to ask, so the
    only available act was the one the boundary forbids.
    """
    res = permitted_senders(agent, decls, roster)
    if res is None:
        return ""
    literal, relayed, dead = res
    who = [f"{s}" for s in literal] + [f"{s} (carries relays: {tok})" for s, tok in relayed]
    line = (f"BOUNDED — only {', '.join(who)} may write to you; every other seat is refused at "
            f"ITS OWN cli and keeps its message" if who else
            "BOUNDED — and NOBODY currently resolves: no seat can reach you at all")
    if dead:
        # Loud rather than omitted: a token nothing carries is indistinguishable, in the bound's
        # own text, from one that works — which is exactly how `master` named nobody for a whole run.
        line += (f" · ⚠ the bound also names {', '.join(dead)}, which NO seat declares — "
                 f"nobody can reach you by that name")
    return line


def inbox_scope_line(base, agent):
    """One line naming the seat's inbox narrowing, or '' for an ordinary seat."""
    entry = closing_entry(base, agent)
    if entry is not None:
        closer = entry.get("closer") or f"closer-{agent}"
        return (f"CLOSING since {entry.get('since', '?')} — inbox is {closer} + leader only; "
                f"peers are refused at the CLI and still hold their message (G-21)")
    scope = broadcast_scope(agent)
    if scope is None:
        return ""
    if scope:
        return (f"special-case seat — of the room's broadcasts you receive only "
                f"{'/'.join(sorted(scope))}; G-20 does not filter direct messages (a `senders:` "
                f"bound can, and the senders: line below reports it)")
    # ⚠ THIS USED TO SAY "direct messages always do", which is FALSE for a bounded seat and was
    # printed to bounded seats: G-20 is about BROADCASTS, and the sender bound is a separate
    # narrowing this line never knew about. Stating a scope you do not compute is how a seat comes
    # to trust a line that contradicts the refusal its senders are getting.
    return ("special-case seat — the room's broadcasts do not reach you; G-20 does not filter "
            "direct messages (a `senders:` bound can, and the senders: line below reports it)")


def closing_reaches(seat, sender, entry):
    """May `sender`'s DIRECT message reach `seat` while it is closing? Only its closer and the
    leader. The closer exception is not optional: the co-write IS a conversation (the closer sends
    its draft `--type ask` and folds in the correction), so a literal no-direct-messages would
    break the very ceremony the state exists for. Leader stays reachable for an abort or a renew."""
    if sender == "leader":
        return True
    expected = (entry or {}).get("closer") or f"closer-{seat}"
    return sender == expected


def cmd_approve(args):
    """Answer a seat's interactive permission/approval prompt: send keys to its
    REGISTERED pane and echo the pane tail so the caller can verify the outcome. This is
    the sanctioned pane-touch for approval gates — inspect the pane (capture-pane) and
    decide BEFORE calling; --keys "" (default) just presses Enter (the highlighted
    option), --keys 1/2/3/n selects that option, --no-enter sends keys without Enter.

    `args.target` is the seat being answered — NEVER the caller (T1: `args.agent` now means
    "who is calling" everywhere, so a target positional must not land on it)."""
    _, _, rows = load_workers(base_dir(args))
    row = current_row(rows, args.target)
    if not row or row.get("active") != "yes" or not row.get("pane"):
        refuse(
            "state",
            f"no ACTIVE pane is registered for '{args.target}', so there is nothing to "
            f"send keys to — the seat never checked in, has checked out, or its pane changed.\n"
            f"Check the roster first: {coord_invocation(args)} workers",
            1)
    pane = row["pane"]
    set_injection_context(action="approve")
    if args.keys:
        tmux_send_text(pane, args.keys)
        time.sleep(0.2)
    if not args.no_enter:
        tmux_send_enter(pane)
    time.sleep(0.8)
    tail, terr = tmux_capture_tail(pane, lines=6)  # (text, err) — printing the tuple was F13
    print(f"sent {args.keys!r}{'' if args.no_enter else ' + Enter'} to {args.target} ({pane}); pane tail:")
    print(tail if not terr else f"(capture failed: {terr})")
    print(c("next: run it again if the tail above still shows the prompt", C_HINT))


def unread_for(args, base, agent, start, blocks=None, gmap=None, observers=None, closing=None):
    """Messages after #start this agent would see on an unfiltered `read` — the same predicate
    `read` uses, so checkin/status/workers never disagree with it. This is the ONE unread
    derivation: it excludes the agent's own sends and honours addressing + observer status, which
    a bare `log tail - cursor` subtraction cannot (that over-reported every seat whose own
    messages were the tail). The optional preloaded log/groups/observers let a caller that lists
    EVERY agent (`workers`) parse each of them once instead of once per row."""
    if blocks is None:
        _, blocks = load_messages(base)
    if not blocks:
        return []
    if gmap is None:
        gmap = group_map(base)
    if observers is None:
        observers, _ = observer_sets(args)
    if closing is None:
        closing = closing_seats(base)
    # Hoisted OUT of the comprehension: `inbox_decls` re-reads every seat descriptor in the
    # package (a glob + N file reads), and inside the filter it ran once PER MESSAGE BLOCK — on a
    # 61k-line log with 409 seats that is millions of reads for one identical dict. Same value,
    # computed once. (Measured: `workers` on run-3 spent 229s of 230s here.)
    decls = inbox_decls(args)
    return [b for b in blocks if b["num"] > start
            and shows_in_inbox(b, agent, gmap, observers, "any", closing, decls)]


def cmd_checkin(args):
    base = base_dir(args)
    # ⚠ `owner` IS A RESERVED BUS ADDRESS AND MAY NOT BE A SEAT NAME
    # (`decisions.md#d-agents-address-owner-not-master`, consequence 2). Refused at the roster's
    # own door — the earliest surface a name can enter this run through — because the token has to
    # mean THE HUMAN on every bus: a seat holding it would silently capture every owner-bound row
    # an agent initiates, and the capture would look exactly like normal delivery. No --force: a
    # name is free to change, and there is no case in which this one must be a seat.
    if args.agent == OWNER_TOKEN:
        refuse(
            "input",
            f"'{OWNER_TOKEN}' is a RESERVED bus address — the token agent-initiated human-bound "
            f"traffic is sent to, ferried to the human by the chat bridge "
            f"(d-agents-address-owner-not-master). No seat may carry it: a seat named "
            f"'{OWNER_TOKEN}' would receive every row meant for the person.\n"
            f"Pick another name and check in again.",
            1)
    # ⚠ `auto` IS RESERVED TOO (D2, 2026-08-19), one clause at this same door and for the same
    # reason: it is the routed types' recipient token, so a seat holding it would silently capture
    # every `stuck` and every routed `ask` in this run, and the capture would look like delivery.
    if args.agent == AUTO_TOKEN:
        refuse(
            "input",
            f"'{AUTO_TOKEN}' is a RESERVED bus address — the token a ROUTED message is sent to "
            f"when the sender does not pick a recipient:\n"
            f"  {coord_invocation(args)} send {AUTO_TOKEN} \"<what you are blocked on>\" "
            f"--type stuck --inline\n"
            f"No seat may carry it: a seat named '{AUTO_TOKEN}' would silently receive every "
            f"routed row in this run.\n"
            f"Pick another name and check in again.",
            1)
    base.mkdir(parents=True, exist_ok=True)
    summary = " ".join(args.summary.split()).replace("|", "/")
    if len(summary) > SUMMARY_MAX:
        refuse(
            "input",
            f"summary is {len(summary)} chars — max {SUMMARY_MAX}.\n"
            "This line is how OTHER agents decide whether your work concerns them and whether "
            "to message you. Rewrite it to state, concretely: what you are changing/producing "
            "and which shared surfaces (records, scripts, views) you touch. No filler.",
            1)
    pane = detect_pane(args.pane)
    # F1 — PANELESS CHECK-IN (owner ruling, 2026-08-17). Same verb, one code path, both lanes. A
    # daemon-launched seat has no tmux pane, and it was ORDERED TO SKIP CHECKIN because of it — so
    # it had no ACTIVE roster row, which is the single cause behind: checkout refused at its state
    # gate (30 of 45 rows attested `exited`/`kit` because the seat could never declare its own
    # ending), the read cursor never persisting, `ready-seats` unable to report RUNNING (twin leader
    # sittings 4 s apart), and `send`/`close-seat` having no handle. Checkin already tolerated an
    # empty pane; what was missing is an IDENTITY to register under.
    #
    # F-6 (owner ruling, 2026-08-21): the identity registered here is the id THIS PROCESS can
    # PROVE is its own — `carrier_self_session()`, the session id of the daemon-minted carrier
    # unit read out of the caller's own /proc/self/cgroup — never "the seat's last open
    # `sessions.csv` row by file order". Selecting by last-open-row bound the 2026-08-20 leader
    # sitting to a stale, never-closed 08-18 row (sessions.csv:61), so the roster carried
    # `sid:d8489a81…` while the carrier unit was `rbtv-worker-a3b2bee1…` — and D43's
    # corroboration (`carrier_corroborated_seat`, an EXACT match of unit suffix against roster
    # token) failed closed on the one lane it was built for. The last-open-row selection remains
    # ONLY as the fallback for paneless callers running under no carrier unit (the attached lane,
    # and caged seats until the cage stops hiding /proc/self/cgroup — bwrap `--unshare-cgroup`).
    if not pane:
        _open_sid = carrier.carrier_self_session() or \
            sessions_open_ids(package_dir(args)).get(args.agent, "")
        if _open_sid:
            pane = SID_PANE_PREFIX + _open_sid
    if is_tmux_pane(pane):
        set_pane_title(pane, args.agent)
    elif pane:
        print(f"paneless check-in: no tmux pane, registered against open session {pane} — wakes "
              f"cannot reach you, so run `read` at your own checkpoints.", file=sys.stderr)
    else:
        print("warning: not inside tmux and no --pane given, and no open sessions.csv row to bind "
              "to, so your row carries no pane and wakes cannot reach you — you must run `read` at "
              "your own checkpoints. Pass --pane %N to bind one.", file=sys.stderr)
    # P37 (zombie double-launch): supersession is the RIGHT answer for a relaunch or a recovery —
    # the prior pane is gone, so nothing else can be holding the name. It is the WRONG answer when
    # the prior pane is still ALIVE: two live sessions then share one roster name, and the run has
    # no way to see it. Only the newest pane is in the roster, so every wake reaches only that one;
    # the own-sender read filter is keyed on the NAME (`unread_for`), so each twin's messages are
    # invisible to the other; and both write the same seat's surfaces as single-writer. Refuse, and
    # name the remedy the protocol requires — confirm the old session is dead (kill it BY PANE ID,
    # never by name) before retrying. `--force` is the deliberate override.
    if not getattr(args, "force", False):
        _, _, existing = load_workers(base)
        prior = current_row(existing, args.agent)
        # ⚠ THE WALL'S PREDICATE IS THE REGISTRY, NOT THE PANE [T4-R8, spec-supervisor §6]. What
        # this wall must stop is TWO LIVE SITTINGS UNDER ONE NAME, and a pane answers a different
        # question: it outlives its harness (so a dead seat's pane refused honest check-ins) and a
        # daemon-lane sitting never had one (so it refused nothing at all). `occupied` collapses
        # the registry's three-valued answer once and fails CLOSED on the unknown arm — where the
        # sitting is UNSUPERVISED the pane is all there is, and it still decides toward refusal.
        if (prior and prior["active"] == "yes" and prior["pane"] and prior["pane"] != pane
                and liveness.occupied(base.parent if base.name == "coordination" else base,
                                      args.agent, prior["pane"] in live_panes())):
            refuse(
                "state",
                f"'{args.agent}' is already checked in on pane {prior['pane']}, and tmux "
                f"says that pane is still ALIVE — checking in from {pane or 'no pane'} would put "
                f"two live sessions under one name.\n"
                f"Neither would see the other's messages (the unread filter is keyed on the name) "
                f"and only this pane would receive wakes.\n"
                f"Confirm the old session is dead first, then retry: inspect it with "
                f"`tmux capture-pane -p -t {prior['pane']}`; if it is a zombie, kill it BY PANE ID "
                f"(`tmux kill-pane -t {prior['pane']}`) — never by name — and check in again.\n"
                f"If you are deliberately running two sessions under this name, re-run with "
                f"--force.",
                1)
        # G-leader-0731-0421 / r-checkout-selfclose (owner, 2026-07-31): the OTHER zombie shape.
        # The name's PRIOR session checked out done, its pane still lives as awaiting-close debt,
        # and this check-in's own later checkout would OVERWRITE that name-keyed debt record
        # (`set_awaiting` is `data[seat] = ...`), orphaning the live pane where no instrument can
        # reach it — `reap` then reports "pane already gone", true of the pane it names, false of
        # the room. Run-3 measured three such orphans resident 14-23 h. Refuse until the debt pane
        # is freed; --force is the same deliberate override as above.
        debt = dict(next((e for s, e, _a, _l in awaiting_debts(base) if s == args.agent), {}))
        if debt.get("pane") and debt["pane"] != pane and liveness.occupied(
                base.parent if base.name == "coordination" else base,
                args.agent, debt["pane"] in live_panes()):
            refuse(
                "state",
                f"'{args.agent}' has an UNSETTLED awaiting-close debt on pane {debt['pane']}, "
                f"and tmux says that pane is still ALIVE — checking in from "
                f"{pane or 'no pane'} now would let this session's later checkout overwrite the "
                f"name-keyed debt record and orphan that pane where reap can no longer see it "
                f"(G-leader-0731-0421).\n"
                f"Free it first: leader runs `{coord_invocation(args)} close-seat {args.agent}` "
                f"(or `{coord_invocation(args)} reap --go` once due) — or inspect and kill BY "
                f"PANE ID: `tmux capture-pane -p -t {debt['pane']}`, then "
                f"`tmux kill-pane -t {debt['pane']}`. Then check in again.\n"
                f"Deliberately checking in over the live debt anyway: --force.",
                1)
    # G-11: a row goes ACTIVE only when a harness process is actually running in its pane. The
    # closer whose multi-line prompt was executed by the pane's SHELL checked itself in from bash
    # — a real row, an honest-looking summary, and nothing running behind it; its "completion"
    # message was believed for seven minutes. The roster is the run's map of what is alive, so the
    # claim is verified at the moment it is made, against the process table rather than the caller.
    # Fail-safe, deliberately asymmetric: only POSITIVE absence refuses. An unreadable process
    # table or pane pid ("cannot tell") passes, since losing a real seat to a false refusal is
    # worse than the defect. COORD_SKIP_HARNESS_CHECK=1 is the escape hatch for an unrecognized
    # harness wrapper.
    if is_tmux_pane(pane) and not process.SKIP_HARNESS_CHECK:
        pids, verifiable = process.pane_harness_pids(pane)
        if verifiable and not pids:
            refuse(
                "environment",
                f"no {'/'.join(HARNESS_PROCS)} process is running in pane {pane}, so this "
                f"check-in would put '{args.agent}' on the roster as ACTIVE with nothing behind it "
                f"(G-11).\n"
                f"This is what a briefing executed by the pane's SHELL looks like: the checkin line "
                f"runs for real while the harness never started. If that is what happened, the "
                f"prompt reached the pane as literal keystrokes — spawn through `launch`/`close`, "
                f"which pass the prompt as a file.\n"
                f"If a harness IS running here under a wrapper this check cannot recognize, re-run "
                f"with COORD_SKIP_HARNESS_CHECK=1 and say so on the log.",
                1)
    superseded = 0
    # The read cursor belongs to the SEAT, not to one session of it: a re-check-in (P1
    # supersession) and a renewed seat (close-seat --renew closes the row BEFORE the fresh
    # session checks in) both used to write lastread=0, so the seat was told the entire log was
    # unread and re-read hundreds of messages it had already been shown. The new row inherits the
    # highest cursor any prior row of the SAME agent reached — never another agent's.
    inherited = 0
    with coord_lock(base):
        path, lines, rows = load_workers(base)
        if not path.exists():
            atomic_write(path, WORKERS_HEADER)
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            rows = []
        displaced = []
        for r in rows:
            same_name = r["agent"] == args.agent
            # P1b: ONE PANE IS ONE HARNESS, SO A SECOND LIVE ROW THERE IS STALE BY CONSTRUCTION.
            # P1 retired ghost rows keyed on the NAME and stopped there, which leaves the mirror
            # shape untouched: one PANE carrying live rows under two NAMES. Measured on run-3's
            # owner door, 2026-08-07 — the seat was renamed `master` -> `goal-master` (keeping
            # `relays: master` so the role word still routed), a later sitting checked in under
            # the OLD name from the SAME pane, and both rows went live. Nothing downstream can
            # survive that: `pane_agent` resolves a pane to `hit[-1]`, so the checkout closed the
            # NEWER name and left the older row ACTIVE with a dead process behind it, and the
            # watch loop's revival arm then relaunched a seat that had just closed cleanly, twice.
            #
            # RETIRING IT BEATS REFUSING IT. A refusal would demand a human close the other row
            # before this session can register — for a state the tool can resolve unambiguously,
            # since the pane's previous occupant is gone the moment a new harness checks in there.
            # It is not silent: the retired row is marked `superseded` like any other, and the
            # displacement is NAMED on the check-in line.
            #
            # NOT MASTER-SPECIFIC. `relays:` exists precisely so a renamed seat keeps its role word
            # (a run that renames its leader declares `relays: leader`), so every future rename
            # arrives here — as does any relaunch into a pane whose prior seat died without a row.
            same_pane = bool(pane) and r["pane"] == pane and r["active"] == "yes"
            if not same_name and not same_pane:
                continue
            # The cursor belongs to the SEAT: a displaced row is ANOTHER seat's reading and must
            # never be inherited, or the new name silently skips messages it has not been shown.
            if same_name and r["lastread"].isdigit():
                inherited = max(inherited, int(r["lastread"]))
            if r["active"] == "yes":
                r["active"] = "no"
                r["checkout"] = f"superseded {now()}"
                lines[r["_line"]] = row_text(r)
                if same_name:
                    superseded += 1
                else:
                    displaced.append(r["agent"])
        new_row = {"agent": args.agent, "active": "yes", "pane": pane, "summary": summary,
                   "checkin": now(), "checkout": "", "lastread": str(inherited)}
        atomic_write(path, "".join(lines) + row_text(new_row))
    note = f" (superseded {superseded} prior row(s))" if superseded else ""
    if displaced:
        note += (f" (RETIRED {len(displaced)} stale row(s) on {pane} held under another name: "
                 f"{', '.join(sorted(set(displaced)))})")
    if inherited:
        note += f" (cursor kept at #{inherited})"
    print(f"checked in: {args.agent} ({pane or 'no pane'}){note} — {summary}")
    # The check-out handoff, DELIVERED (s12-08). Placed HERE — after the check-in is recorded and
    # reported, before the placement-drift flag — so the seat is handed its predecessor's note at
    # the first moment it is a checked-in session, and `session_trace_safe` guards it for exactly
    # the reason it guards the session trace a few lines below: bookkeeping ABOUT a check-in must
    # never become a gate ON it. A seat that cannot check in is worse than a handoff shown twice,
    # and every branch inside that could reasonably fail already handles itself.
    _hd_ok, _hd_err = session_trace_safe(deliver_handoff, args, base, args.agent)
    if _hd_err:
        print(c(f"WARNING handoff delivery skipped — {_hd_err}. Your checkin STANDS. If a handoff "
                f"was waiting it is still `unread=yes`, so the next check-in of this seat will "
                f"show it.", C_DEAD), file=sys.stderr)
    # PLACEMENT DRIFT: the seat checks its OWN pane against what its descriptor declares.
    #
    # DETECTION, NOT PREVENTION, and the distinction is the honest half of this: a pane opened BY
    # HAND never passes through `launch`, so no validation there can ever see it — which is exactly
    # how the trigger instance happened (a hand-renewal into the wrong window). This is the only
    # reachable half. It also cannot self-correct: a seat cannot move its own pane without killing
    # it, and a pane whose purpose is human contact must never be moved to tidy a layout — a door
    # in the wrong window is cosmetic, a door killed for the layout is an outage. So it FLAGS and
    # leaves, and the operational fix stays a human's.
    if is_tmux_pane(pane):
        _decl = next((w["window"] for w in launch.discover_workers(workers_dir(args))
                      if w["agent"] == args.agent), "")
        _actual = tmux_pane_window_name(pane)
        if _decl and _decl != "yes" and _actual and _actual != _decl:
            print(c(f"placement drift: your descriptor declares `window: {_decl}` but this pane is "
                    f"in '{_actual}'. Nothing here moves it — a seat cannot move its own pane "
                    f"without killing it. Report it; the layout fix is operational stewardship.",
                    C_DEAD), file=sys.stderr)
    # 7.37: the seat's own checkin is where its native session id becomes resolvable — see
    # session_backfill_native. Never allowed to break a checkin (session_trace_safe).
    nat, nerr = session_trace_safe(session_backfill_native, args, args.agent)
    if nerr:
        print(c(f"WARNING sessions.csv native-session-id NOT backfilled — {nerr}. Your checkin "
                f"stands, but NO fallback surface carries this id and nothing backfills it later "
                f"— unlike the check-out warning, this loss is real.", C_DEAD), file=sys.stderr)
    elif nat.startswith("!unresolved"):
        print(c(f"WARNING sessions.csv: this seat has an OPEN session row and its "
                f"native-session-id could NOT be resolved — {nat[12:]}. Task 7.32's native resume "
                f"cannot use this row.", C_DEAD), file=sys.stderr)
    elif nat:
        print(f"sessions.csv: native session id recorded ({nat})")
    # 7.96: the seat is TOLD WHO IT IS, on EVERY successful check-in. Until now the ids reached the
    # seat only down `session_backfill_native`'s failure branch — measured 0 of 104 run-2 sessions
    # — so in practice a seat never learned its own session-id and could not name the scratchpad
    # the convention gives it. Same stamp, same read, one line: the write records WHEN the session
    # came alive (`checkin`) and the read reports WHICH session it is.
    # ⚠ `session_trace_safe`, like every bookkeeping call around this check-in: a trace that cannot
    # be written must never become a gate on the act it records. The line prints EITHER WAY, with
    # UNRESOLVED where an id could not be reached — a failure that printed nothing would be read as
    # a check-in that had nothing to report.
    _ci, _cierr = session_trace_safe(session_checkin, args, args.agent)
    _sid, _snat, _ = _ci if (_ci and not _cierr) else ("", "", "")
    if _cierr:
        print(c(f"WARNING sessions.csv checkin stamp NOT written — {_cierr}. Your checkin STANDS; "
                f"the trace cannot say when this session came alive.", C_DEAD), file=sys.stderr)
    _sfolder = next((w["folder"] for w in launch.discover_workers(workers_dir(args))
                     if w["agent"] == args.agent), None)
    print(session_identity_line(args.agent, _sid, _snat, seat_scratchpad(_sfolder, _sid)))
    # T1: from here the seat never types its own name again — every other command resolves it.
    waiting = unread_for(args, base, args.agent, inherited)
    if waiting:
        print(c(f"next: {coord_invocation(args)} read — {len(waiting)} message(s) already waiting "
                f"for you", C_HINT))
    else:
        print(c(f"next: {coord_invocation(args)} status — nothing waiting yet", C_HINT))


# ---- the check-out handoff block (s12-06, AMENDED 2026-08-03) -----------------------------
#
# R-14 (`rulings.md`): this effort touches NOTHING that deals with memory — no dreamer, no closer
# work, no compounding — WITH ONE EXCEPTION: the handoff on check-out, a simple form of short-term
# memory. THIS IS THAT EXCEPTION, AND ITS WHOLE EXTENT. There is no rotation, no compaction, no
# indexing and no summarizing of `memory.md` here, and nothing reads a block back except
# `s12-08`'s unread flip.
#
# ⚠⚠ OWNER RULING, 2026-08-03 — `memory.md` IS THE HANDOFF, AND THE RENEW CHECK-OUT REPLACES THE
# FILE WHOLESALE. A seat's memory is now exactly one thing: the current handoff block. No body, no
# prior blocks, no history. The seat does not maintain a state doc beside it and nothing accretes
# in it between sessions — what the successor is handed is the WHOLE of what it inherits.
#
# ⚠ AND THAT RULING IS WHAT MAKES THE REPLACE SAFE — the file is HOMOGENEOUS BY CONSTRUCTION now,
# because this writer is the only thing that ever writes it. The superseded bar above this line
# read "APPEND AT EOF, NEVER PARSE, NEVER REWRITE", and it was right FOR ITS ERA: `memory.md` was
# then heterogeneous by construction — some opened with YAML frontmatter
# (`agent:`/`updated:`/`sessions-closed:`), some at a `#` heading — so any shape-assuming write
# corrupted exactly the files it did not anticipate. A wholesale replace of a heterogeneous file
# destroys a seat's state doc; a wholesale replace of a file that holds ONE block and nothing else
# destroys nothing, and is the point: it is what makes "keep ONLY the latest" mechanical rather
# than a prune pass over a log (protocol item 9; the run-3 measurement that forced it — 133
# delivered blocks / 214 KB stacked on one seat — cannot recur when the file cannot stack).
#
# The block format is UNCHANGED and deliberately so: HTML comments, invisible in rendered
# markdown, unable to collide with a heading, `v=1` on BOTH delimiters so a half-written file is
# DETECTABLE. Every reader — `handoff_blocks`, `handoff_truncated`, `deliver_handoff`, the
# executor's re-read — is untouched by this amendment and keeps parsing exactly what it did.

HANDOFF_TOKEN = "coord:handoff"   # the delimiter word — and the one literal a note body may not carry
HANDOFF_V = "v=1"                 # on BOTH delimiters, so a half-written block is detectable
HANDOFF_STAMP_FMT = "%Y-%m-%dT%H:%M:%S"
# The note's TARGET size, in lines. A WARNING THRESHOLD, NEVER A GATE: the note is the seat's whole
# memory now, so refusing an oversized one would destroy the handoff at the moment it is being made
# — the checkout stands and the seat is told to tighten it. `protocol.md` item 9 carries this same
# number in prose; if one moves, both move.
HANDOFF_MAX_LINES = 120


def handoff_stamp_text(when):
    """The block's `stamped=` value — ONE formatter, for BOTH of its consumers.

    s12-07 stores this exact string in `awaiting-close.json`'s `handoff_stamp`, and the two must be
    byte-identical: the record is what a later reader uses to find the block it describes. So the
    clock is read ONCE at the call site and formatted HERE for the block and for the record alike.
    Two `datetime.now()` calls can straddle a second — a whole second apart, with nothing able to
    notice — and a second format string is the same drift with an extra way to go wrong."""
    return when.strftime(HANDOFF_STAMP_FMT)


def handoff_block_text(seat, session, disposition, note, when=None):
    """The handoff block, VERBATIM per `stage-1-2-gate-checkout-spec.md` §3.

    `session=` is NEVER omitted — a missing key breaks a positional reader, an explicit `unknown`
    does not. `unread=yes` is the ONLY mutable attribute (`s12-08` flips it to `no` after it has
    printed the block at the successor's check-in); every other attribute is written once here and
    never touched again.
    """
    stamp = when or datetime.now()
    return (
        f"<!-- {HANDOFF_TOKEN} {HANDOFF_V} seat={seat} session={session or 'unknown'} "
        f"disposition={disposition} stamped={handoff_stamp_text(stamp)} unread=yes -->\n"
        f"## Handoff → next session of `{seat}` ({stamp.strftime('%Y-%m-%d %H:%M')})\n"
        f"\n"
        f"{note}\n"
        f"\n"
        f"<!-- /{HANDOFF_TOKEN} {HANDOFF_V} -->\n")


def session_id_open(args, seat):
    """The seat's OPEN `sessions.csv` session-id, or `''` — read-only and never fatal.

    Read BEFORE the checkout body runs, because `session_close` stamps `ended` on exactly this row:
    the handoff must name the session that WROTE it, not a row already closed out from under it.
    LAST open row wins, the same rule `session_close` itself applies. `''` becomes `session=unknown`
    at the block rather than a dropped attribute.

    7.475: the row selection moved OUT to `sessions_open_ids` and is not reimplemented here — the
    same move `session_disposition` made to `sessions_last_ended` at 7.237, for the same reason:
    a second question now asks about this same open row (7.475's fallback guard) and two copies of
    the selection would drift. WHAT THIS FUNCTION RETURNS DID NOT CHANGE — same rows, same file
    order, same last-wins, same `''` on every surface that cannot answer. The `try` stays because
    `package_dir` itself can raise on an unresolvable package, which is BEFORE the reader is
    reached and so outside what `sessions_open_ids` can catch.
    """
    try:
        return sessions_open_ids(package_dir(args)).get(seat, "")
    except (OSError, ValueError, csv.Error):
        return ""


def write_handoff(base, memory_path, block):
    """REPLACE `memory.md` with `block` under `coord_lock` + `atomic_write`, then VERIFY it landed.

    Returns `(ok, detail)`; `detail` names the failure when `ok` is False.

    ⚠ WHOLESALE, BY OWNER RULING (2026-08-03) — the file's ENTIRE content after this call is the
    one block passed in. Nothing prior is read, merged, pruned or carried: there is no body to
    preserve, no delivered block to splice out at its indices, and no separator to negotiate,
    because a seat's `memory.md` holds exactly one handoff and nothing else. This is a REPLACEMENT
    of the append-plus-prune writer that stood until that ruling, not an option beside it — the
    prune existed only to bound a file that could stack, and a file that is rewritten whole cannot.
    The section header above carries why the old bar (append at EOF, never rewrite) was correct for
    a heterogeneous `memory.md` and why it stopped applying to a homogeneous one.

    ⚠ THE VERIFICATION IS NOT CEREMONY, IT IS THE POINT. `coord_lock` IS NEVER FATAL — a sandboxed
    seat whose package is read-only (codex EROFS) proceeds WITHOUT the lock after one note — so
    this write can be concurrent, and the replace can fail on a filesystem that accepted the open.
    A silent half-write loses the ONE artifact the successor is promised, at the exact moment the
    seat believes it handed over. So the file is RE-READ and must equal the composed bytes EXACTLY.
    Equality is what a wholesale write can assert and an append could not: the old writer had to
    ask two weaker questions (is the block IN the file, and is the file's last delimiter a CLOSING
    one) because everything else in the file was somebody else's bytes. Byte-equality subsumes
    both — a truncated write cannot equal the block. `handoff_truncated` stays exactly where it is
    as the READER's verdict on a file this writer did not produce.
    """
    try:
        with coord_lock(base):
            atomic_write(memory_path, block)
        landed = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    except (OSError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if landed != block:
        return False, ("memory.md does NOT hold the composed block after the write — the replace "
                       "did not land, or landed partially (a lockless write on a read-only "
                       "package, or a replace that failed)")
    return True, ""

# ---- the check-in handoff DELIVERY (s12-08) -----------------------------------------------
#
# The delivery half of the handoff, and it COPIES THE MESSAGE CURSOR'S ORDERING deliberately:
# `cmd_read` calls `persist_cursor` AFTER the messages are rendered, and that ordering is what
# makes "shown" and "read" the same event. The `unread=` attribute is this mechanism's cursor and
# it moves at the same moment, for the same reason.
#
# WHAT SATISFIES EACH REQUIREMENT (`stage-1-2-gate-checkout-spec.md` §4/§5):
#   survives a crash        the block is on disk from the moment call 2 returns
#   re-delivers if unshown  the flip FOLLOWS the print, so a kill anywhere before it leaves
#                           `unread=yes` and the next check-in shows the same block again
#   keyed on (seat, unread) the lookup reads the seat FOLDER and the ATTRIBUTE, never the `seat=`
#                           author — so a revived successor of a CRASHED seat is handed its own
#                           predecessor's block (D2). NO `workers.md` COLUMN: that row is
#                           per-SESSION and is superseded at re-check-in, while the handoff must
#                           outlive a crash that left no successor row at all
#   idempotent              flipping an already-`no` block is a no-op, exactly as `persist_cursor`
#                           skips a cursor that would not move
#
# ⚠ THE FLIP IS A TARGETED SPLICE AT THE SELECTED BLOCK'S OWN INDICES — NEVER A `replace_all`. A
# whole-file `replace("unread=yes", "unread=no")` would mark EVERY historical block read in one
# act and destroy the re-delivery property for all of them at once.


def handoff_blocks(text):
    """Every COMPLETE handoff block in `text`, in file order.

    Each entry carries `head` (the opening comment, verbatim), its `head_start`/`head_end` span —
    so the flip can splice at an INDEX rather than match a string two byte-identical headers could
    both answer to — plus `attrs` and the `body` between the delimiters.

    Attributes are read BY NAME, never by position: the writer emits `session=unknown` rather than
    dropping the key precisely so a reader never has to count tokens, and a reader that counted
    them would break the day a key is added.

    An opener with no closer is NOT a block and is skipped here; the FILE-level truncation verdict
    belongs to `handoff_truncated`, which is what the caller acts on.
    """
    opener = f"<!-- {HANDOFF_TOKEN} {HANDOFF_V} "
    closer = f"<!-- /{HANDOFF_TOKEN} {HANDOFF_V} -->"
    found, i = [], 0
    while True:
        start = text.find(opener, i)
        if start < 0:
            return found
        head_end = text.find("-->", start)
        if head_end < 0:
            return found                  # a header cut mid-line: nothing after it can parse
        head_end += 3
        end = text.find(closer, head_end)
        nl = text.find("\n", head_end)
        i = head_end
        if end < 0 or nl < 0 or nl > end:
            continue
        attrs = {}
        for tok in text[start + len(opener):head_end - 3].split():
            key, _, val = tok.partition("=")
            attrs[key] = val
        found.append({"head": text[start:head_end], "head_start": start, "head_end": head_end,
                      "attrs": attrs, "body": text[nl + 1:end].strip("\n")})
        i = end + len(closer)


def handoff_truncated(text):
    """True when the file's LAST handoff delimiter is an OPENING one.

    THE READER'S OWN VERDICT, and since the 2026-08-03 amendment it is the ONLY holder of this
    test: `write_handoff` now asserts BYTE-EQUALITY with the block it composed, which subsumes
    this shape (a truncated write cannot equal the block). This function is not thereby dead —
    it judges files this writer did not produce: a hand-edited `memory.md`, one left behind by an
    older build, or one a crash caught mid-replace on a filesystem that does not honour rename
    atomicity. What it must NOT become is a second opinion about what a half-written block looks
    like; it states the same shape the writer refuses to leave behind.
    """
    return text.rfind(f"<!-- /{HANDOFF_TOKEN}") < text.rfind(f"<!-- {HANDOFF_TOKEN}")


def handoff_stamp_human(stamp):
    """The block's `stamped=` value rendered for the successor's eyes.

    Parsed against `HANDOFF_STAMP_FMT` — the format the WRITER used — never against a second copy
    of it; a literal here is the same drift `handoff_stamp_text` exists to prevent. An unparseable
    value is shown RAW rather than dropped: a time that looks wrong still tells the reader more
    than no time at all.
    """
    try:
        return datetime.strptime(stamp, HANDOFF_STAMP_FMT).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return stamp or "an unrecorded time"


def flip_handoff_read(base, memory_path, head):
    """Mark the block whose header is `head` READ: ONE line, spliced at its own indices, under
    `coord_lock` + `atomic_write`. Returns `(ok, detail)`.

    ⚠ NEVER `replace_all`, and never a replacement computed over the whole file. The block is
    RE-LOCATED under the lock and rewritten BY INDEX, so two byte-identical headers (one seat, one
    session, one second) can never make this flip the wrong one — and every other block's bytes,
    read or unread, are carried through untouched.

    `head` is the header this process actually PRINTED. If the file moved underneath and the last
    unread block is no longer that one, NOTHING is written: marking a block read that nobody was
    shown is the one outcome worse than showing one twice.
    """
    new = ""
    try:
        with coord_lock(base):
            text = memory_path.read_text(encoding="utf-8")
            unread = [b for b in handoff_blocks(text) if b["attrs"].get("unread") == "yes"]
            if not unread:
                # Idempotent, the same way `persist_cursor` no-ops a cursor that would not move:
                # a concurrent successor already marked it, and re-writing the file to say what it
                # already says is pure race surface.
                return True, "already read"
            block = unread[-1]
            if block["head"] != head:
                return False, ("the file changed under the delivery — its LAST unread block is no "
                               "longer the one that was printed, so nothing was marked read")
            new = (text[:block["head_start"]]
                   + head.replace("unread=yes", "unread=no", 1)
                   + text[block["head_end"]:])
            atomic_write(memory_path, new)
            landed = memory_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if landed != new:
        return False, ("the flip is NOT on disk after the write — the replace failed, or a "
                       "concurrent writer overwrote it")
    return True, ""


def deliver_handoff(args, base, seat):
    """Show this seat's unread handoff, THEN mark it read. NEVER blocks the check-in.

    Non-fatal in every direction, and deliberately SILENT in most of them — a seat with no folder,
    no `memory.md`, an unreadable one, or nothing unread has nothing to be told. The two loud
    branches are the two where silence would mislead: a TRUNCATED block (printing its tail would
    dump an unbounded slice of the file into the seat's context) and a FLIP THAT FAILED after the
    block was already printed.
    """
    found = next((w for w in launch.discover_workers(workers_dir(args)) if w["agent"] == seat), None)
    folder = found.get("folder") if found else None
    if folder is None:
        return
    memory_path = folder / "memory.md"
    try:
        text = memory_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return
    if handoff_truncated(text):
        print(c(f"WARNING {memory_path} ends in a TRUNCATED handoff block — its opening delimiter "
                f"has no matching closer, so where that note ENDS is unknown and NOTHING was "
                f"printed or marked read. Printing the tail instead would pour an unbounded slice "
                f"of the file into this session. The text above the break is intact; repair the "
                f"file by hand and tell leader.", C_DEAD), file=sys.stderr)
        return
    unread = [b for b in handoff_blocks(text) if b["attrs"].get("unread") == "yes"]
    if not unread:
        return
    block = unread[-1]
    print(f"handoff waiting — written by the previous session of this seat at "
          f"{handoff_stamp_human(block['attrs'].get('stamped', ''))}:")
    print(block["body"])
    print(f"(marked read now; it stays in {memory_path} until your own renewal REPLACES the file "
          f"with your handoff — owner ruling 2026-08-03: memory.md holds your current handoff and "
          f"nothing else, so anything above that you still need, you carry into your own note)")
    # ⚠ THE BROAD CATCH IS THE POINT, AND IT BELONGS HERE RATHER THAN AT THE CALLER. The block is
    # already on the seat's screen; anything this raises must land on the ONE loud branch below,
    # which says "you were shown it, it was NOT marked read". The caller's guard would report the
    # delivery as SKIPPED instead — a statement that is simply false once the print has happened.
    try:
        ok, why = flip_handoff_read(base, memory_path, block["head"])
    except Exception as exc:                                   # noqa: BLE001 — deliberate
        ok, why = False, f"{type(exc).__name__}: {exc}"
    if not ok:
        print(c(f"WARNING the handoff above was NOT marked read — {why}. It is STILL "
                f"`unread=yes` in {memory_path}, so the NEXT check-in of this seat will be shown "
                f"it again. RE-DELIVERY BEATS LOSS: act on it once, and say so on the log if it "
                f"keeps repeating.", C_DEAD), file=sys.stderr)


# ---- M4-11 (task 7.126): THE CHECK-OUT FAST PATH — DELETED (`one-readiness-predicate`) ---------
#
# The module path constant, the hook wrapper and its call site in `cmd_checkout` are GONE, with the
# retired Python advancement job they loaded. Recorded here rather than erased silently, because
# the seam they occupied is one a reader will propose re-cutting.
#
# WHY IT WENT. THREE implementations of "is this seat ready to launch" existed at once — this
# file's `ready_seat_rows`, a Python job under `jobs/`, and the daemon's own JS seeding pass. They
# drifted, and the drift is what stalled the live goal. The ruling collapses readiness onto THIS
# file (`ready-seats --json` is the one answer) and has the daemon's seeding pass consume it. Two
# of the three go away; this call was the arm-gated entry into one of them and it had fired exactly
# once ever, on a throwaway goal.
#
# ⚠ AND CHECK-OUT DOES NOT DISPATCH, DELIBERATELY. The re-seed stays the driver because it is a
# PULL: every cadence it asks disk what should be true and makes it true, so running it a thousand
# times equals running it once and a missed pass costs latency and nothing else. Making check-out
# dispatch makes it a PUSH, which must be delivered exactly once — a pane killed mid-close, a daemon
# restarting, an enqueue that throws, and the goal is stranded permanently while every file on disk
# says it should have advanced. That is why the deleted hook was wrapped in a catch-everything, and
# a path that must swallow its own failures can never be the only path. If cadence latency ever
# matters, check-out may POKE the daemon to run a pass now; losing that poke must cost ten seconds,
# never the run.


# ---- 7.676: THE DONE-CONTRACT CHECK — what the seat DECLARED it would produce ------------------
#
# THE SECOND HALF OF THE 2026-08-09 INCIDENT. The first half was that no honest ending EXISTED
# (`incomplete`, on the record enum above). This half is that NOTHING WAS EVER VERIFIED: check-out
# wrote `done` — the one value that advances a DAG edge — without opening a single thing the seat
# was supposed to have produced. The two halves are one defect: a tool that cannot express failure
# and does not look is a tool whose `done` carries no information at all.
#
# THE DECLARATION IS THE io-spec `## Outputs` BLOCK IN THE SEAT'S OWN seat.md BODY (D3,
# 2026-08-18 — the `outputs:` frontmatter key is RETIRED and refused on sight; the block is the
# ONE surface, read through `iospec_outputs`, the shared resolver the admission gate mirrors).
# It is the first machine-checkable half of a done gate this kit has had. G-57's standing note
# (on `descriptor_findings`) records why: the descriptor's owned-surfaces claim and its done gate
# are PROSE, "and that stays open until a `surfaces:` frontmatter key makes the claim a field".
# This is that field for the OUTPUT half. ⚠ It does not settle G-57: `surfaces:` would be what a
# seat may WRITE (a permission, single-writer arbitration); a declared OUTPUT is what a seat must
# have PRODUCED (a debt, checked at the ending). Same paths, often; never the same question.
#
# ⚠⚠ UNDECLARED IS NOT VERIFIED, AND IS NOT REFUSED EITHER (D5 default, 2026-08-19). A seat
# with no `## Outputs` section at all makes no output claim; D5's spirit ("done = verified
# claim") plus RC-A both point at claims that were MADE and cannot be verified. Refusing an
# undeclared seat would refuse most of the POPULATION at its check-out — the one act R-8 says
# must always be available to a finishing seat. Its `done` STANDS, recorded with `none-declared`
# IN THOSE WORDS.
#
# ⚠ D5 DOES REFUSE THE THIRD STATE. Between declared and undeclared sits the D3 planner
# extension's `outputs-undeclarable`: a seat whose `## Outputs` section EXISTS but yields ZERO
# resolvable tokens (a prose block). That IS a claim, and it cannot be verified — the
# stools/meet leader freeze of 2026-08-19. Checkout refuses the WORD `done` and records
# `unverified` (D32, 2026-08-20 — it was `incomplete` plus a stamped reason until then); the
# `outputs-verified` field still carries the undeclarable text. A reader tells a CHECKED `done`
# from an unverifiable claim BY THE DISPOSITION ALONE, with no note to read and no prefix to parse.
def _declared_output_goal_dir(w):
    """The GOAL FOLDER a BARE relative declared output names — `<goal>/seats/<seat>` and the
    legacy `<goal>/workers/<seat>` are the only two shapes a descriptor folder takes
    (`workers_dir`, which is where both spellings are decided). None when the descriptor sits
    anywhere else: nothing to resolve against, so only the `cwd` base is read."""
    folder = w.get("folder")
    if folder is None:
        return None
    parent = Path(folder).parent
    return parent.parent if parent.name in ("seats", "workers") else None


def resolved_outputs(w):
    """[(declared token, RESOLVED absolute path)] for ONE seat's declared outputs (D3: the
    io-spec `## Outputs` tokens, parsed once at `discover_workers`).

    THE ONE RESOLUTION OF A DECLARED OUTPUT IN THIS MODULE, and it is split out of
    `declared_outputs` because D4's seed needs the SAME resolution from a different place: the
    readiness sweep hands a launching seat its predecessors' output paths, and it must not compute
    them a second way. Resolving a declared output twice is how the check-out's `MISSING: /a/b`
    and the successor's seed end up naming different files for one declaration.

    Relative paths resolve against the seat's `cwd`, already absolutized by `discover_workers` at
    the ONE parse point (a relative `cwd:` otherwise resolves against nothing). It reads the
    descriptor dict it is handed and touches no disk — the PRESENCE question is `declared_outputs`'
    and stays there.

    ⚠ THE SECOND BASE IS `declared_outputs`', NOT THIS FUNCTION'S (D36 extension, 2026-08-20).
    A BARE relative token means GOAL-RELATIVE to the other half of this grammar
    (`envelope/cage-admission.js#admitDeclaredOutputs`, in its own refusal words: "a declared output
    is GOAL-RELATIVE") and to every task that writes one. This function keeps the `cwd` base
    UNCHANGED because its second caller is D4's SEED, whose contract (RS-28) is that a
    predecessor's relative output resolves against that predecessor's own `cwd` — a settled
    ruling this is not the place to reopen. The PRESENCE check reads both bases; see there."""
    return [(d, str(Path(d) if os.path.isabs(d) else Path(w["cwd"]) / d)) for d in w["outputs"]]


def _goal_root_dotslash(d):
    """`./<name>.<ext>` with NO further `/` — D90's narrow goal-root spelling. Split out of the
    presence check so the STAMP can ask the same question; see `output_candidates`."""
    if not str(d).startswith("./"):
        return False
    rest = str(d)[2:]
    return bool(rest) and "/" not in rest


def output_candidates(w, declared, resolved):
    """The bases a declared output may live at, IN THE ORDER THE PRESENCE CHECK TRIES THEM.

    ⚠⚠ ONE DEFINITION, TWO CALLERS, AND THE SECOND CALLER IS WHY THIS EXISTS. The presence check
    in `declared_outputs` reads these candidates; `stamp_checkout_ending` must stamp the SAME path
    the check graded, because the ending store re-runs its own mechanical check (§1.3) against
    whatever pointer it is handed. Until this was factored out, that stamp re-derived a base of its
    own — `{package}/workers/{seat}` — and every seat in a `seats/`-layout package had its VERIFIED
    `done` overturned into `failed: outputs-missing`, naming a path that was never the seat's. The
    kit said present, the store said missing, and they were looking at different files.

    Two graders of one fact is the defect class §4.1 exists to remove; this keeps the two READS in
    one place so they cannot disagree again."""
    cands = [Path(resolved)]
    goal = _declared_output_goal_dir(w)
    if goal is not None and not os.path.isabs(declared) and (
            not str(declared).startswith(("./", "../")) or _goal_root_dotslash(declared)):
        cands.insert(0, Path(goal) / declared)   # the DECLARED meaning, checked first
    return cands


def declared_outputs(args, seat):
    """(declared, missing, has_block, chat) — the seat's OWN declared outputs (io-spec
    `## Outputs` tokens), which of them are not on disk, whether an `## Outputs` section exists
    at all (D3: a section yielding ZERO tokens is `outputs-undeclarable`, a distinct loud state
    the check-out records — never collapsed into `none-declared`), and whether that section
    declares the typed NON-FILE output `chat` (D36, 2026-08-20 — a zero-token section that IS a
    declaration, so the `done` stands).

    `declared` is the raw list as the descriptor wrote it; `missing` holds RESOLVED paths, because
    a seat told `plan.md is missing` when it is looking straight at a `plan.md` has been told
    nothing — the value it needs is which directory the check looked in.

    PRESENT means: a directory that exists, or a file that exists AND IS NON-EMPTY. The zero-byte
    arm is not fussiness — an empty file is what a crashed or never-run writer leaves behind, and
    "the path exists" would grade that as produced, which is the exact grading this check exists to
    stop. Relative paths resolve against the seat's `cwd`, already absolutized by `discover_workers`
    at the ONE parse point (a relative `cwd:` otherwise resolves against nothing).

    A seat with no descriptor at all returns `([], [], False, False)` — undeclared, like a
    descriptor with no block. It is the same answer for the same reason: nothing was declared, so nothing is
    checkable, and this function does not get to invent the difference."""
    for w in launch.discover_workers(workers_dir(args)):
        if w["agent"] != seat:
            continue
        # 7.711 — refused HERE, and only here, though the defect is detected at the parse point:
        # `discover_workers` is read by launch, status and the sensors, and killing those over
        # another seat's descriptor typo would be a worse failure than the one being fixed. This is
        # the one caller for which the value is load-bearing.
        if w["outputs_defect"]:
            refuse("input",
                   f"'{seat}' has a RETIRED `outputs:` frontmatter declaration and this "
                   f"check-out will not read it: {w['outputs_defect']}.\n"
                   f"  descriptor: {w['briefing']}\n"
                   f"Move the declaration, then re-run checkout. A seat with no `## Outputs` "
                   f"section is admitted and the record says `none-declared`. Refusing here "
                   f"costs the re-run only: nothing was written, nothing was exported, your "
                   f"roster row is still ACTIVE.",
                   1)
        # ⚠⚠ TWO BASES, AND THE MEASUREMENT THAT FORCED THEM (D36 extension, 2026-08-20).
        # A BARE relative token (`planning/current/findings-clarity.md`) is GOAL-RELATIVE — that
        # is what `envelope/cage-admission.js#admitDeclaredOutputs` means by it in its own refusal
        # text ("a declared output is GOAL-RELATIVE"), what every task's `<scope>` `Write:` clause
        # says in words ("relative to the goal folder"), and what D36 projects. This check read
        # ONLY the `cwd` base — the SEAT folder — so the two readers of ONE declaration looked in
        # two different directories. Measured on the two production goals: all 17 declared tokens
        # on live seats are bare and goal-relative; 16 exist at the goal folder and ONE at the
        # seat folder. Without this, D36's projection would have turned a soft `unverified` into a
        # HARD refusal ("MISSING: <seatdir>/planning/…") for ~50 seats that had done the work.
        # BOTH bases count as present, and that is deliberate rather than a failure to choose:
        # the `cwd` base is D4's seed contract (RS-28) and the `./plan.md` spelling this file
        # documents, so dropping it would break declarations that are correct today. The widening
        # it costs is a file of the SAME relative name under the seat's own scratchpad — which is
        # the seat's own work either way. What is NOT widened: a token absent at both bases is
        # still refused, and the refusal NAMES THE GOAL-RELATIVE PATH, the one the author meant.
        #
        # ⚠⚠⚠ A THIRD, NARROW WIDENING (D90, 2026-08-22): `./<name>.<ext>` WITH NO FURTHER `/` ALSO
        # GETS A GOAL-ROOT CANDIDATE. `#594`'s unclosable half: `goal.md` and `milestones.csv` are
        # written AT THE GOAL ROOT, not under any subdirectory, so there is no bare relative token
        # for them at all — `_IOSPEC_PATHISH` demands a `/`, and the only sanctioned slashless
        # spelling this file documents is `./name.md`. Before D90 that spelling was cwd-ONLY (the
        # line above), which made the two tasks that write these files structurally undeclarable:
        # not absent from the grammar, EXCLUDED from it by the same rule that protects RS-28.
        # `_goal_root_dotslash` narrows the lift to EXACTLY that shape — one path segment after
        # `./`, nothing deeper — so it cannot collide with `resolved_outputs`' cwd-only reading of
        # a DEEPER dot-token (`./out/report.md`, pinned by the `blocky` OU fixture below, and by
        # RS-28/RS-29's `./plan.md`/`./other.md` seed fixtures — all of which stay cwd-only,
        # unresolved, because `resolved_outputs` itself is UNTOUCHED by this widening: D4's SEED
        # contract is not reopened, only THIS presence check gets a second candidate). Additive,
        # same as the bare-token widening above: a `./name.md` seat-private file that only exists
        # at cwd still passes (the cwd candidate is still tried), and a `./name.md` that only
        # exists at the goal root now ALSO passes — never a token that used to resolve now failing.
        def _present(p):
            try:
                return p.is_dir() or (p.is_file() and p.stat().st_size > 0)
            except OSError:
                return False         # unreadable is NOT produced — the seat is told the path

        missing = []
        for _d, _resolved in resolved_outputs(w):
            if is_output_template(_d):
                continue
            _cands = output_candidates(w, _d, _resolved)
            if not any(_present(p) for p in _cands):
                missing.append(str(_cands[0]))
        return w["outputs"], missing, w["outputs_declared"], w["outputs_chat"]
    return [], [], False, False


def cmd_checkout(args):
    # s12-05 / D2: `--handoff` is the note the seat's SUCCESSOR reads, so it belongs only to a
    # checkout that OPENS a next session. A done-checkout writes no handoff. Refused FIRST — before
    # identity resolution, before the roster read, before the export — so an argument error costs
    # nothing: at this point nothing has been read, written, captured or muted.
    renew = getattr(args, "renew", False)
    handoff = getattr(args, "handoff", None)
    handoff_file = getattr(args, "handoff_file", None)
    # 7.676: the seat's own declaration that its done-contract is UNMET. Refused HERE, beside the
    # other argument errors and before identity resolution, for the reason stated above: at this
    # point nothing has been read, written, captured or muted, so a bad invocation costs a re-run.
    incomplete = (getattr(args, "incomplete", None) or "").strip()
    # s12-07: set by CALL 2 only, and read at the single `set_awaiting` both paths fall through to.
    # The done path records "" because it wrote no block — an empty stamp is the honest value,
    # never a placeholder time.
    handoff_stamp = ""
    # ⚠ THE TWO NOTE SOURCES ARE EXCLUSIVE AND THE REFUSAL IS EXPLICIT, not argparse's mutually
    # exclusive group: a seat that passed both is holding two versions of the note it is about to
    # be judged on, and a bare usage string does not tell it which one would have won. Nothing has
    # been read, written or closed at this point, so the refusal costs it nothing but the re-run.
    if handoff is not None and handoff_file is not None:
        refuse(
            "input",
            f"--handoff and --handoff-file both carry your successor's note, so passing both "
            f"leaves it undecided which one becomes this seat's memory — and that memory is now "
            f"the WHOLE of what your successor inherits (owner ruling 2026-08-03). Nothing was "
            f"written and nothing was closed.\n"
            f"Pick one: `--handoff \"<note>\"` for a short one typed inline, or `--handoff-file "
            f"<path>` for one you wrote to a file.",
            2)
    if (handoff is not None or handoff_file is not None) and not renew:
        refuse(
            "input",
            f"--handoff/--handoff-file carry what the NEXT session of this seat must do, so they "
            f"need a checkout that opens one: pass --renew with it. A done-checkout has no "
            f"successor to hand anything to, and accepting the note here would file a handoff "
            f"nobody is ever booted to read.\n"
            f"Renewing this seat: {coord_invocation(args)} checkout --renew\n"
            f"Done for good:      {coord_invocation(args)} checkout",
            2)
    # 7.676: `--incomplete` and `--renew` are OPPOSITE STATEMENTS about the same session and the
    # refusal says which, rather than letting argparse print a usage line. `--renew` says THIS SEAT
    # CONTINUES — a successor boots and inherits the handoff; `--incomplete` says THIS SEAT ENDS
    # UNFINISHED — no successor, and the leader picks the work up. A seat holding both has not
    # decided which, and guessing for it is how the DAG ends up advancing on a seat that meant to
    # stop. ⚠ Renewal is ALREADY the honest ending for "unfinished but continuing" — that is why
    # this is a refusal and not a merge of the two.
    if incomplete and renew:
        refuse(
            "input",
            f"--incomplete and --renew say opposite things about this session, so passing both "
            f"leaves it undecided whether a successor boots. Nothing was written and nothing was "
            f"closed.\n"
            f"Unfinished, and the seat CONTINUES (a successor picks it up):  "
            f"{coord_invocation(args)} checkout --renew\n"
            f"Unfinished, and the seat ENDS (leader picks it up):            "
            f"{coord_invocation(args)} checkout --incomplete \"<what is unmet>\"",
            2)
    # ⚠ AN EMPTY REASON IS REFUSED, and this is the one place in this command where an empty string
    # is not just an absent value. `--incomplete ""` records an ending nobody can act on — the
    # leader inherits "this seat stopped" with no statement of WHAT is unmet, which is the same
    # dead end as the `done` this flag exists to replace, reached one step later.
    if getattr(args, "incomplete", None) is not None and not incomplete:
        refuse(
            "input",
            f"--incomplete needs a REASON, and it was passed empty. The reason IS the value of "
            f"this ending: it is what the leader reads to decide who picks the work up and from "
            f"where, and an ending with no reason is the uninformative `done` this flag exists to "
            f"replace. Nothing was written and nothing was closed.\n"
            f"Say what is unmet: {coord_invocation(args)} checkout --incomplete \"<what your "
            f"briefing asked for that does not exist>\"",
            2)
    # ⚠ THE FILE IS READ HERE — BEFORE identity resolution, before the roster read, before the
    # export, and therefore before any state change at all. An unreadable path is an argument
    # error, and an argument error must cost the seat nothing: the alternative is discovering it
    # after the arm, with the wakes already muted and the note still only in a file.
    if handoff_file is not None:
        try:
            handoff = Path(handoff_file).read_text(encoding="utf-8").rstrip("\n")
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            refuse(
                "input",
                f"--handoff-file {handoff_file} could not be read as UTF-8 text — "
                f"{type(exc).__name__}: {exc}. Nothing was written and nothing was closed; your "
                f"session is untouched and your note is not lost.\n"
                f"Check the path (it is resolved from THIS process's working directory, so pass "
                f"it absolute), then re-run `{coord_invocation(args)} checkout --renew "
                f"--handoff-file <path>`.",
                2)
        if not handoff.strip():
            refuse(
                "input",
                f"--handoff-file {handoff_file} is EMPTY. It would replace this seat's memory.md "
                f"with a handoff that says nothing, and your successor would boot with nothing at "
                f"all (owner ruling 2026-08-03: memory.md IS the handoff). Nothing was written and "
                f"nothing was closed.\n"
                f"Write the note into that file, then re-run the same command.",
                2)
    base = base_dir(args)
    me = resolve_agent(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    if not row or row["active"] != "yes":
        refuse(
            "state",
            f"'{me}' has no ACTIVE roster row, so there is no session to end — you "
            f"never checked in, or you already checked out.\n"
            f"See the roster: {coord_invocation(args)} workers",
            1)
    # Tasks 41+159: parked wait is `--incomplete`, never `--renew`. A posted unanswered owner
    # ask is the kit-witnessed wait; `--renew` would fork an immediate successor (no delay, no
    # wake) and was the 70s busy-loop on system-health/plan-completeness-reviewer. Refuse HERE,
    # before any write. Relay / ending-stamp waits have no table row — protocol + briefing
    # mandate `--incomplete` for those; this door covers the owner-ask half mechanically.
    if renew:
        _park_asks = posted_open_asks_for_seat(args, me)
        if _park_asks:
            refuse(
                "state",
                f"'{me}' has {len(_park_asks)} posted ask(s) to the owner that nobody has "
                f"answered, so this check-out will not `--renew`. `--renew` boots a successor "
                f"NOW; a wait on the owner's answer is not a continuation of this seat — it is "
                f"an unfinished ending. `--incomplete` and `--renew` stay opposite statements.\n"
                + "".join(f"  UNANSWERED: {b['ask_id']} to the owner — "
                            f"{truncate(str(b.get('evidence_pointer') or ''), 160)}\n"
                          for b in _park_asks) +
                f"Park the wait: {coord_invocation(args)} checkout --incomplete "
                f"\"asked the owner in "
                + ", ".join(str(b['ask_id']) for b in _park_asks)
                + " and ended with no answer\"\n"
                f"That stamps `blocked-on-human` (disarmed until `ask-answered`). Nothing was "
                f"written and nothing was closed.",
                1)
    # ---- 7.676 (+ D3): VERIFY BEFORE ASSERTING `done` -------------------------------------------
    #
    # THREE QUESTIONS AT ONE GATE, and every one of them asks whether this `done` is TRUE: did this
    # seat produce what it DECLARED it would (7.676, `outputs:`), did it write the guard value a
    # live `after` member READS (D3, `guarded_pairs`), and is it sitting on an ASK the owner has not
    # answered (D8, `open_asks`). Everything below about gating, refusing and not downgrading
    # applies identically to all three.
    #
    # ⚠ THE THIRD IS NOT A DEBT THE SEAT CAN DISCHARGE — an answer is the owner's to give, so its
    # remedy is `--incomplete`, not "do it and re-run". Its own block below carries that
    # distinction; it is named here so a reader of this header does not carry the first two's shape
    # onto it.
    #
    # ⚠ IT GATES THE `done` PATH ALONE. `--renew` asserts nothing finished (a successor is being
    # booted precisely because the work continues), and `--incomplete` is the seat ALREADY saying
    # the contract is unmet — checking a claim nobody made would refuse the honest ending, which
    # is the one arm that must never be harder to reach than the dishonest one.
    #
# ⚠ IT REFUSES; IT DOES NOT DOWNGRADE — for the three questions below (missing outputs, unwritten
# guard, open owner-ask). Silently rewriting the seat's `done` into `incomplete` would have the
# KIT declare a fact about work only the SEAT can witness — the same misgrading the writer bound
# bars, and it would land the seat's ending with no reason attached, since the kit has none to
# give. The seat is told exactly which declared paths are absent and handed the two honest
# endings; which one is true is its call, not this function's.
#
# ⚠ D5 (2026-08-19) IS THE ONE DOWNGRADE, AND IT IS LOUD. An `outputs-undeclarable` answer is a
# fact the KIT DID witness (it looked at the declared `## Outputs` surface and found nothing
# gradeable). A hard refuse+exit-1 would loop the seat: its cage denies write access to its own
# seat.md, so it cannot add the missing tokens. Recording nothing is the 08-19 freeze made worse.
# So the WORD `done` is refused on stderr in this same register, the ending is recorded as
# `unverified` (D32, 2026-08-20 — it was `incomplete` with a stamped reason until then), and
# `outputs-verified` still carries the undeclarable text. (ii) of the paragraph above is answered
# by the WORD: `unverified` says, on its own, which of the two questions the kit could not answer,
# and it says it without a reason column, a side file or anything to parse. (i) is answered by
# being loud, not silent.
    #
    # ⚠ AND IT RUNS BEFORE THE EXPORT AND BEFORE THE ROSTER FLIP. A refusal here costs the seat
    # nothing but the re-run — its session is untouched, its transcript uncaptured, its row still
    # ACTIVE — which is what makes refusing safe at all on the one act a finishing seat must always
    # be able to complete.
    # WHAT THE CHECK ACTUALLY DID, IN WORDS, ONTO THE DURABLE RECORD. R-7: a fact recorded only in
    # a perishable surface is not recorded — printing "nothing to check" at a check-out nobody is
    # watching leaves the same unreadable `done` behind. These are the four honest answers, and
    # `none-declared` is the one that carries 7.676's admission: THIS `done` WAS NOT CHECKED,
    # because the briefing declared nothing to check. A reader can now tell the two apart.
    _outputs_note = ("not-checked (renew — no completion asserted)" if renew
                     else "not-checked (seat declared incomplete)")
    # D32: the D5 gate's own flag, declared beside the note it is computed from. FALSE everywhere
    # the gate does not run, so the `checkout_disposition` expression below reads one name on
    # every path rather than a value that exists only on one branch.
    outputs_unverified = False
    outputs_missing = False
    _declared_paths, _missing_paths = [], []
    if not renew and not incomplete:
        _declared, _missing, _has_block, _chat = declared_outputs(args, me)
        _declared_paths, _missing_paths = list(_declared), list(_missing)
        # D3's three honest answers, in words: verified (tokens declared and present),
        # `outputs-undeclarable` (an `## Outputs` section EXISTS but is prose — zero resolvable
        # tokens; loud, never a silent nothing; D5 refuses the WORD `done` on this answer),
        # `none-declared` (no section at all — D5 default: the `done` STANDS).
        # D36 (2026-08-20): the `chat` arm sits AHEAD of the undeclarable one and reads
        # `none-declared` IN THOSE WORDS — a typed non-file output is a DECLARATION the kit can
        # read, so there is nothing on disk to verify and nothing to refuse. It is the same
        # admission `none-declared` has always carried (this `done` was not checked), with the
        # reason named: the seat declared conversation, not files.
        _outputs_note = (f"{len(_declared)} declared output(s) verified present" if _declared
                         else ("none-declared — this seat declares the typed `chat` output (a "
                               "NON-FILE product, D36 2026-08-20): there is no path to check, "
                               "so this `done` asserts completion NOTHING VERIFIED"
                               if _has_block and _chat
                               else "outputs-undeclarable: zero tokens — the io-spec `## Outputs` "
                               "section yields no resolvable path token (backticked, with a `/` "
                               "and an extension), so this `done` asserts completion NOTHING "
                               "VERIFIED" if _has_block
                               else "none-declared — this `done` asserts completion NOTHING "
                                    "VERIFIED (the seat.md carries no io-spec `## Outputs` "
                                    "section)"))
        if _missing:
            outputs_missing = True
            print(refusal_text(
                "state",
                f"'{me}' declared {len(_declared)} output(s) and "
                f"{len(_missing)} {'is' if len(_missing) == 1 else 'are'} missing or empty. "
                f"`done` is not written. Ending is `failed` / outputs-missing.\n"
                + "".join(f"  MISSING (or empty): {p}\n" for p in _missing)),
                  file=sys.stderr)
        # ---- D3 (`one-readiness-predicate`): THE SECOND QUESTION AT THE SAME GATE ---------------
        #
        # Does this seat owe a GUARD VALUE that is not on disk? A guarded edge
        # `<me>[<key>=<value>]` needs two things to advance: this seat's own `done`, and a recorded
        # value for `<key>`. Without this question a seat checks out `done` having never written
        # its value, every guarded successor stays BLOCKED on an unruled guard, and the run stalls
        # pointing at a seat that has already departed and cannot be asked.
        #
        # ⚠ NOTHING NEW IS DECLARED. The keys a seat owes are `guarded_pairs()` — the pairs a LIVE
        # `after` member actually references — filtered to this seat. A seat no edge guards owes
        # nothing and never reaches the refusal; the debt is created by the DAG, not by this gate.
        #
        # ⚠⚠ ONLY THE `done` BRANCH IS GATED, and this is inside the `not renew and not incomplete`
        # block for exactly that reason. `incomplete`, `failed`, `exited`, `renew` and `revive` are
        # UNTOUCHED. A seat that cannot produce its value must still be able to END HONESTLY —
        # gating those would rebuild the 2026-08-09 defect the `incomplete` disposition was minted
        # to fix, where the only ending a seat could reach asserted a completion it had not made.
        # The honest ending must never be harder to reach than the dishonest one.
        #
        # ⚠ AND IT REFUSES RATHER THAN WRITING A DEFAULT. Inventing a value would have the kit
        # assert a fact about work only the seat witnessed — the same misgrading the writer bound
        # bars, and the same reason the outputs check above refuses instead of downgrading.
        _guard_pairs = ready.guarded_pairs(package_dir(args))
        _guard_have = ready.load_guard_values(base)
        _guard_owed = sorted({k for (_s, k) in _guard_pairs
                              if _s == me and (me, k) not in _guard_have})
        if _guard_owed:
            refuse(
                "state",
                f"'{me}' owes {len(_guard_owed)} guard value(s) that "
                f"{'is' if len(_guard_owed) == 1 else 'are'} NOT on disk, so this check-out will "
                f"not record `done`. A guarded `after` member reads YOUR value to decide whether "
                f"its edge is admitted, and `done` is the ONE disposition that advances the DAG — "
                f"checking out without the value leaves every guarded successor BLOCKED on an "
                f"unruled guard, with the only party who could have answered already departed. "
                f"Nothing was written, nothing was exported and your roster row is still ACTIVE.\n"
                + "".join(f"  UNWRITTEN: `{me}[{k}=…]`, read by "
                          f"{', '.join('`' + str(t) + '`' for t in _guard_pairs[(me, k)])}\n"
                          f"    write it: {coord_invocation(args)} rule-guard {me} {k}=<value> "
                          f"--source \"<where you measured it>\" --go\n"
                          for k in _guard_owed) +
                f"Then re-run: {coord_invocation(args)} checkout\n"
                f"Or END HONESTLY, if you cannot establish the value — the run records that you "
                f"said so, and leader picks the work up:\n"
                f"  {coord_invocation(args)} checkout --incomplete \"<why the guard is "
                f"unestablished>\"",
                1)
        # ---- D8 (`one-readiness-predicate`): THE THIRD QUESTION AT THE SAME GATE ---------------
        #
        # IS THIS SEAT SITTING ON A QUESTION THE OWNER NEVER ANSWERED? `d-block-and-queue-
        # mechanical-hold` says a `fallback: block-and-queue` seat that asked the owner and exited
        # with no answer is not `done` TO THE DAG — its dependents do not start. That hold lived in
        # `supervisor/seeding.js`, inside the `after`-cell walk `seatState` used to do. D1 DELETED that
        # walk: seeding now consumes `ready-seats --json`, and readiness is read off the CHECK-OUT.
        # So the seat still reads `live` locally and is not re-dispatched, but its SUCCESSORS are
        # gated by coord alone — and a held seat checking out `done` released every one of them,
        # its execution record saying `blocked`, its check-out saying `done`, only the latter read.
        # The hold is expressed HERE or it is expressed nowhere.
        #
        # ⚠ SAME THREE RULES AS THE TWO ABOVE. Only the `done` branch is gated (this is inside the
        # `not renew and not incomplete` block), so `incomplete`, `failed`, `exited`, `renew` and
        # `revive` are UNTOUCHED — the honest ending must never be harder to reach than the
        # dishonest one, which is the 2026-08-09 defect and the reason the escape exists at all. It
        # REFUSES rather than downgrading, and it runs BEFORE the export and the roster flip, so a
        # refusal costs the seat the re-run and nothing else.
        #
        # ⚠ ONE READER, AND IT IS THE ENDING STORE (spec-state-store §2.1). This gate keyed on
        # `open_asks(messages.md, to=owner)` — coord's BUS predicate — while the engine keyed the
        # same fact on the `open_asks` TABLE. One fact, two sources: a posted ask with no bus row
        # held the engine and not this door, and a bus ask nobody delivered held this door and not
        # the engine. The store is reachable from inside the cage: this very command already stamps
        # its ending through `ending_store` a few lines on, so the kit door is the seat's door.
        # Nothing here re-derives ask/answer pairing.
        # ⚠⚠ WHAT SETTLES AN ASK IS THE REAP (§2.8): an authorized reply in that exact thread flips
        # the row `closed` and signals the relaunch in ONE transaction. `--re <#>` on the bus
        # settles a bus row and no longer lifts this hold.
        #
        # ⚠ AN UNDELIVERED ASK DOES NOT HOLD, AND ITS ABSENCE FROM THIS REFUSAL IS DELIBERATE —
        # not an oversight (owner ruling 2026-08-11, `d-parked-ask-autonomous-workaround`). The
        # parked case now has a FIELD instead of a mirrored ladder: §3 sets `posted=1` only once
        # delivery is acknowledged, so `posted=0` IS "nobody was told", and no answer can EVER
        # arrive for it. `ask_parked_at_gate`'s re-derivation of the ferry's ladder is therefore
        # gone from this door — the store carries the fact the ladder was predicting. A released
        # seat is NOT silent: the note below names the reason on the seat's own output and on its
        # durable disposition record, so a reader can tell "measured and released" from
        # "never asked".
        #
        # ⚠ IT REFUSES AND NEVER DEGRADES. An unreachable store must not release a held seat, so a
        # store error is a refusal here — the opposite direction from `ready-seats`, whose broad
        # `except` protects a fail-closed-per-goal seeding pass that must not lose its other
        # verdicts to a bad read.
        _bq_fm = briefing_frontmatters(workers_dir(args)).get(me)
        _bq_all = []
        if _bq_fm and _fm_fallback(_bq_fm[0]) == FALLBACK_BLOCK_AND_QUEUE:
            try:
                _bq_all = ending_store.list_open_asks(package_dir(args), seat=me, posted=None)
            except ending_store.EndingStoreError as _exc:
                refuse("state",
                       f"'{me}' declares `fallback: block-and-queue`, so this check-out must read "
                       f"the ending store's open asks before it may record `done` — and the store "
                       f"could not be read: {_exc}. Nothing was written. This refuses rather than "
                       f"releasing, because an unreadable store must never advance a successor on "
                       f"a question that may still be open.", 1)
        _bq_open = [a for a in _bq_all if int(a.get("posted") or 0) == 1]
        _bq_parked = [a for a in _bq_all if int(a.get("posted") or 0) != 1]
        if not _bq_open and _bq_parked:
            _bq_note = (f"owner-ask hold NOT applied: {len(_bq_parked)} open ask(s) to the owner "
                        f"were never POSTED (§3 `posted=0`) — nobody was told, so no answer can "
                        f"settle them")
            _outputs_note += f" · {_bq_note}"
            print(c(f"note: {_bq_note}. Your `done` STANDS (the wave continues). You are expected "
                    f"to have PROCEEDED on your authored autonomous workaround — record the "
                    f"derivation in this goal's decisions.md / doubts.md for the owner to review "
                    f"on his return (d-s14-autonomous-dod).", C_HINT))
        if _bq_open:
            refuse(
                "state",
                f"'{me}' declares `fallback: block-and-queue` and has {len(_bq_open)} posted ask(s) "
                f"to the owner that nobody has answered, so this check-out will not record `done`. "
                f"That arm is this seat's OWN declaration that it blocks on its question, and "
                f"`done` is the ONE disposition that advances the run's DAG — recording it here "
                f"starts every successor on the assumption your question was settled "
                f"(`d-block-and-queue-mechanical-hold`). Nothing was written, nothing was exported "
                f"and your roster row is still ACTIVE.\n"
                + "".join(f"  UNANSWERED: {b['ask_id']} to the owner — "
                            f"{truncate(str(b.get('evidence_pointer') or ''), 160)}\n"
                          for b in _bq_open) +
                f"END HONESTLY — this is the way out, and the only one you can reach on your own, "
                f"because the answer is not yours to produce:\n"
                f"  {coord_invocation(args)} checkout --incomplete \"asked the owner in "
                + ", ".join(str(b['ask_id']) for b in _bq_open) + f" and ended with no answer\"\n"
                f"It does NOT advance your successors, which is the point: the run records that "
                f"you said so and leader picks the work up.\n"
                f"THE ONE OTHER ENDING, if it is TRUE: the answer LANDED while you were working. "
                f"Re-run a plain checkout — if the reply reached that thread the ask has been "
                f"REAPED and this gate passes. (An ask settles when an authorized reply lands in "
                f"its own thread, spec-state-store §2.8 — never on a bus row's `--re <#>`.)\n"
                 f"⚠ YOUR QUESTION WAS DELIVERED — the ask carries `posted=1`, which is set only "
                 f"once delivery to the owner was acknowledged (§3). Retracting it to get past this "
                 f"gate would discard a question he can still answer; an unposted ask, where nobody "
                 f"could be told, does not reach this refusal at all.",
                 1)
        # ---- D5 (2026-08-19): AN UNVERIFIABLE `done` IS NOT `done` ------------------------------
        #
        # `outputs-undeclarable` used to pass this gate freely and still record `done` — the
        # stools/meet leader freeze (RC-A). D5: `done` = verified claim, always. The note is
        # already computed (do not overwrite it with "not-checked (seat declared incomplete)");
        # raising this flag here makes `checkout_disposition` resolve to `unverified` at the one
        # place it is computed, so both remaining surfaces agree.
        # ⚠ D32 (2026-08-20): THE FLAG IS ITS OWN NAME AND NOT THE `incomplete` REASON STRING.
        # Until D32 this branch assigned `incomplete = "outputs-unverified: …"`, which recorded
        # the kit's unverifiable-done in the SEAT'S OWN word for unfinished work — measured cost:
        # 7 rows of finished work reading `incomplete`, and `incomplete` meaning two opposite
        # things at once. The word is the discriminator now, so nothing downstream parses a
        # prefix off a reason string to tell the two endings apart.
        # ⚠ D29 (2026-08-20), EXTENDED 2026-08-20 by the owner's `r-owner-122-b` (a): a
        # CONVERSATIONAL CHAIR is EXEMPT from this one downgrade — its product is conversation,
        # not files, so its `done` STANDS without path tokens. D29 named the summoned chair;
        # the extension adds the staff chair (`leader` — the `consultant` chair is deleted
        # [T2-R17, D-7-ruling]), whose `## Outputs` is prose for the identical reason of NATURE,
        # not by an authoring oversight.
        # Keyed on `is_conversational_chair` (CONVERSATIONAL_CHAIRS), never a seat name at this
        # site; ordinary seats — including the 171 `agent_type: staff` PLANNING seats, which are
        # not chairs — remain bound by the `elif` below, unchanged.
        # ⚠ D36 (2026-08-20) — THE TYPED NON-FILE OUTPUT, and it is LOUD on the accepted path.
        # A `- Schema: chat` bullet is a DECLARATION, so this branch never reaches the downgrade
        # below at all (`_outputs_note` opens `none-declared`, not `outputs-undeclarable`) — but
        # a `done` that was not checked must say so where a reader sees it, exactly as the chair
        # exemption does. There is no `outputs-verified` COLUMN to carry it: `sessions.csv` holds
        # the disposition and the writer, and the note has always lived on this output.
        # The VERIFIED answer, said out loud for the same reason the three below are: the note
        # is the only account of what this gate actually did, and `sessions.csv` has no column
        # for it. A `done` a reader cannot tell from an unchecked one is the 2026-08-09 defect.
        if _declared:
            print(f"outputs check: {_outputs_note}")
        elif _has_block and _chat:
            print(f"outputs check: '{me}' declares the typed `chat` output (D36, 2026-08-20) — "
                  f"a NON-FILE product, so there is no path on disk to check and this `done` "
                  f"STANDS. Recorded `none-declared`: {_outputs_note}")
        elif _outputs_note.startswith("outputs-undeclarable") and is_conversational_chair(me):
            print(f"outputs check: '{me}' is a conversational chair — exempt (D29, extended "
                  f"2026-08-20): a chair's product is conversation, not files, so this `done` "
                  f"STANDS with zero path tokens declared.")
        elif _outputs_note.startswith("outputs-undeclarable"):
            outputs_unverified = True
            print(refusal_text(
                "state",
                f"'{me}' asked to record `done` but its io-spec `## Outputs` section yields no "
                f"resolvable path token, so this check-out will not record `done`. `done` is a "
                f"VERIFIED claim (D5, 2026-08-19) and this seat's declared outputs cannot be "
                f"verified — the section exists and is prose. The ending is recorded as "
                f"`unverified` (D32, 2026-08-20) — NOT `incomplete`, which stays the word for a "
                f"seat that declares its OWN work unfinished; no DAG edge advances.\n"
                f"  LOOKED AT: the io-spec `## Outputs` block in this seat's descriptor\n"
                f"  FOUND: zero resolvable path tokens (backticked, with a `/` and an extension)\n"
                f"Declare real path tokens in that `## Outputs` block (a seat cannot edit its own "
                f"seat.md from inside the cage — that is the leader's / materializer's act), or "
                f"end with an explicit `--incomplete \"<why>\"` next time so the record carries "
                f"YOUR reason rather than this kit-stamped one."),
                  file=sys.stderr)
    # ONE variable, computed ONCE after the verify gate (D5/D32 may flip it to `unverified`).
    # Both remaining writers (`session_close` then `set_awaiting`) read this name.
    #
    # ⚠ THE `unverified` ARM SITS AHEAD OF THE `incomplete` ONE AND CANNOT COMPETE WITH IT: the
    # D5/D32 gate runs inside `if not renew and not incomplete`, so a seat that declared its own
    # ending never reaches the flag. The order is stated rather than relied upon.
    checkout_disposition = ("renew" if renew else "unverified" if outputs_unverified
                            else "incomplete" if incomplete else "done")
    if outputs_missing:
        checkout_kind = "outputs-missing"
    elif renew:
        checkout_kind = "incomplete"
    elif outputs_unverified:
        checkout_kind = "outputs-missing"
    elif incomplete:
        checkout_kind = "incomplete"
    else:
        checkout_kind = "done"
    checkout_diagnostic = ("context full" if renew
                           else (incomplete if incomplete else ""))
    park_on_owner = bool(incomplete) and bool(posted_open_asks_for_seat(args, me))
    _checkout_landed = []
    if renew:
        if handoff is None:
            checkout_renew_arm(args, base, me)
            return
        # ---- CALL 2 (s12-06): the handoff lands FIRST, then the ordinary checkout body runs. ----
        #
        # THE ORDER IS LOAD-BEARING. Everything in the body below is irreversible from the seat's
        # side — the export is taken, the roster row is flipped, the session row is closed — so a
        # handoff written after it would be written by a session that no longer exists to be told
        # it failed. Written first, verified, and only then does anything close.
        #
        # ⚠ THE THREE VALIDATIONS BELOW DUPLICATE `checkout_renew_arm`'s, ON PURPOSE. Call 1
        # refuses a folderless and a `close: mechanical` seat before it arms anything — but CALL 2
        # IS REACHABLE WITHOUT CALL 1: nothing forces the two-step, a seat can type the second
        # command first, and a descriptor can change between the two. A guard that only ever fires
        # behind another guard stops holding the day someone finds the other door.
        if HANDOFF_TOKEN in handoff:
            refuse(
                "input",
                f"your note contains the literal `{HANDOFF_TOKEN}`, which is the delimiter word of "
                f"the block it would be written into. Escaping it would leave the block grammar "
                f"ambiguous for every later reader, so it is REFUSED instead and the grammar stays "
                f"decidable. Nothing was written and nothing was closed — your note is not lost.\n"
                f"Re-word that phrase, then re-run: {coord_invocation(args)} checkout --renew "
                f"--handoff \"<what the next session of this seat must do>\"",
                2)
        seat = next((w for w in launch.discover_workers(workers_dir(args)) if w["agent"] == me), None)
        if seat is not None and seat.get("mechanical_close"):
            refuse(
                "input",
                f"'{me}' declares `close: mechanical` (G-23), so it is memoryless BY DESIGN — no "
                f"memory.md, and therefore nowhere for a handoff to land. The owner ruled this "
                f"seat OFF the self-service renew path PERMANENTLY, not provisionally "
                f"(`d-mechanical-no-self-renew`, 2026-07-29). Nothing was written and nothing was "
                f"closed — your note is not lost.\n"
                f"Its renewal is the LEADER-SIDE close-and-relaunch path instead — end this "
                f"session with `{coord_invocation(args)} checkout`, and leader brings the next one "
                f"up with `{coord_invocation(args)} close-seat {me} --renew`.",
                2)
        folder = seat.get("folder") if seat else None
        if folder is None:
            refuse(
                "input",
                f"'{me}' has no seat FOLDER — its descriptor is a flat file, so there is no "
                f"`{me}/memory.md` for this handoff to be written to, and carrying it to your "
                f"successor is the whole point of this path. Nothing was written and nothing was "
                f"closed — your note is not lost.\n"
                f"End this session with `{coord_invocation(args)} checkout` instead; leader "
                f"relaunches the seat if it must come back.",
                2)
        memory_path = folder / "memory.md"
        # The session id is resolved HERE, before the body: `session_close` below stamps `ended` on
        # exactly the row this reads, and the block must name the session that WROTE it.
        # ONE clock reading, formatted ONCE, for both the block and the awaiting-close record
        # (s12-07). Letting `handoff_block_text` take its own `datetime.now()` and computing the
        # record's stamp separately would put two readings around one write, and the pair would
        # disagree by a whole second whenever they straddled one — silently, and only sometimes.
        handoff_when = datetime.now()
        handoff_stamp = handoff_stamp_text(handoff_when)
        handoff_ok, handoff_why = write_handoff(
            base, memory_path,
            handoff_block_text(me, session_id_open(args, me), "renew", handoff,
                               when=handoff_when))
        if not handoff_ok:
            refuse(
                "state",
                f"HANDOFF NOT WRITTEN — {handoff_why}. Your session is UNTOUCHED: nothing was "
                f"exported, the roster still shows you active, and no close was recorded. The "
                f"refusal is deliberate — closing on top of a handoff that is not on disk would "
                f"destroy the one artifact this renewal exists to produce, at the moment you "
                f"believe you handed over.\n"
                f"Keep your note. Check that {memory_path} is writable, then re-run "
                f"`{coord_invocation(args)} checkout --renew --handoff \"<note>\"`. If it fails "
                f"again, tell leader and end with `{coord_invocation(args)} checkout`.",
                1)
        print(f"handoff written: {memory_path}")
        _checkout_landed.append(f"handoff at {memory_path}")
        # ⚠ TAUGHT AT THE MOMENT IT IS TRUE, NEVER ONLY IN A DOC. The seat has just replaced its
        # own memory and this is the last instant at which it can still add to the note; a rule
        # stated anywhere else is read long before or long after the one act it governs.
        print(f"⚠ THAT NOTE IS NOW THE ENTIRE MEMORY OF THIS SEAT. {memory_path} holds it and "
              f"nothing else — your successor is handed exactly what you just wrote and NOTHING "
              f"ELSE (owner ruling 2026-08-03). Every open loop, live watch-item and standing "
              f"instruction that is not IN it is gone.")
        # The size WARNING — loud, and deliberately NOT a gate. The note is already on disk and the
        # checkout STANDS: refusing here would destroy the handoff to punish its length, which is
        # the one outcome worse than an over-long note. Counted on the note the seat supplied, not
        # on the composed block, so the number the seat is told matches the text it wrote.
        _hd_lines = len(handoff.splitlines())
        if _hd_lines > HANDOFF_MAX_LINES:
            print(c(f"WARNING your handoff is {_hd_lines} lines — the target is ~"
                    f"{HANDOFF_MAX_LINES} (protocol item 9). THE CHECKOUT STANDS and the note is "
                    f"written; nothing was refused. But a note this long is one your successor "
                    f"reads at boot in full, and length is where the live items get lost among "
                    f"the narrative. Tighten it before your next renewal: state what is IN FLIGHT, "
                    f"what comes NEXT, and what was RULED OUT — not what happened.", C_DEAD),
                  file=sys.stderr)
    # T3: the export is the seat's last durable artifact and was routinely forgotten — mechanize
    # it instead of teaching it (protocol item 8). --no-export is the escape for a dead pane.
    # It runs FIRST of the three closing acts because it is the only one that is not a CLOSE: it
    # copies the transcript and the ending stamp below reads its path as evidence.
    out, err = "", "--no-export"
    if not getattr(args, "no_export", False):
        out, err = export_transcript(args, me, "checkout")
        print(f"transcript: {out}" if not err else f"transcript skipped — {err}")
    # ── THE ENDING IS STAMPED FIRST, BEFORE ANY SURFACE SAYS THE SESSION IS OVER ───────────────
    #
    # This block used to sit BELOW `session_close` and the roster flip, and that order had a hole
    # with no floor: the ending store is the one surface the cage did not open (family 8, 2026-08-
    # 27), so `stamp_seat_declare` refused `attempt to write a readonly database` for every caged
    # seat — AFTER `sessions.csv` already read `ended` and the roster already read `active=no`.
    # A closed row is a row the supervisor no longer walks (`attest.py#close_session_seat` /
    # `#attest_exit_seat` take OPEN sessions), so nothing stamped the ending after the refusal,
    # no staff mail was minted, the leader was never woken, and the DAG edge never advanced. The
    # seat had no retry either: a second `checkout` refuses "no ACTIVE roster row". Measured on
    # `scratch-tool-reach-note`/`plan-verifier`, 2026-08-27 19:32Z.
    #
    # ORDER IS THE FIX, and it is the ONE ordering under which a refusal costs nothing: with the
    # ending first, a failed stamp leaves `sessions.csv` OPEN and the roster ACTIVE, so the seat
    # can simply run `checkout` again and the supervisor still sees a live session it will attest
    # if the seat dies instead. `session_close` staying first would need the refusal to UNDO two
    # writes on two files — a compensating rollback that can itself fail, on the exact surface
    # whose write just failed.
    #
    # D5 IS UNCHANGED: a failed durable-ledger write still REFUSES the checkout (below). D5 rules
    # that a failed ledger write is not a done; it does not rule which refusing write goes first.
    # And this is now the order `attest.py#attest_exit_seat` already ran in — export, ending
    # stamp, close the session row — so the supervisor's reconstruction of a finished seat and the
    # seat's own check-out leave the same surfaces in the same sequence.
    #
    # s12-07: WHICH checkout this was, ASSERTED here rather than inferred later. Both paths — done
    # and renew — fall through to this ONE call site, and `renew` is the branch discriminant, in
    # scope on this very line. It is passed EXPLICITLY on both arms even though `done` is the
    # default: at the one place the answer is known, a value a reader must chase to a signature is
    # not an assertion.
    #
    # dag-08: `writer` is declared EXPLICITLY, and this is the seat's OWN path — the occupant is
    # reporting a fact about itself. Declaring it here is what puts this call under the writer
    # bound, so `exited` is refused on this path by construction.
    try:
        stamped = stamp_checkout_ending(
            args, me, checkout_kind,
            declared=_declared_paths + _missing_paths,
            diagnostic=checkout_diagnostic,
            evidence=((_missing_paths[0] if _missing_paths else None)
                      or out or f"checkout:{me}"),
            park_on_owner=park_on_owner)
        print(f"ending store: {me} {stamped.get('ending') if isinstance(stamped, dict) else checkout_kind}"
              f"{('/' + stamped['reason_class']) if isinstance(stamped, dict) and stamped.get('reason_class') else ''}")
        _checkout_landed.append(f"ending store: {checkout_kind}")
    except ending_store.EndingStoreError as exc:
        _already = "; ".join(_checkout_landed) if _checkout_landed else "none"
        refuse(
            "state",
            f"ending-store write FAILED — {exc}. Checkout REFUSED; NOTHING was closed — "
            f"`sessions.csv` still holds your OPEN session row and the roster still reads you "
            f"ACTIVE, so run this same checkout again once the store is reachable. Surfaces "
            f"already landed: {_already}.",
            1)
    # Durable ledger next (after the verify gate; after the handoff write on call 2, which has its
    # own must-land-first contract; after the ending stamp, per the block above). A failed
    # sessions.csv write REFUSES the checkout — a failed ledger write is not a done (D5). No
    # swallow, no kit-for-seat proxy.
    try:
        sid = session_close(args, me)
    except Exception as exc:
        _already = "; ".join(_checkout_landed) if _checkout_landed else "none"
        refuse(
            "state",
            f"sessions.csv write FAILED — {type(exc).__name__}: {exc}. Checkout REFUSED; "
            f"the durable ledger is the first CLOSING write of this act after the ending stamp "
            f"(and after a call-2 handoff, when one landed). Surfaces already landed: "
            f"{_already}.",
            1)
    if sid:
        print(f"sessions.csv: {sid} ended")

    def flip(r):
        r["active"] = "no"
        r["checkout"] = now()

    update_row(base, me, flip)
    print(f"checked out: {me}")
    # G-134: the seat's half of the lifecycle is now done and its resources are NOT freed — only
    # `close-seat` kills the pane. Assert that debt here, at the one moment every input is known
    # for certain, instead of leaving a later pass to reconstruct it from roster + tmux + fs.
    #
    # dag-09 (LG-9): ONE VARIABLE, READ BY BOTH SURFACES. `awaiting-close.json` is the live
    # declaration and `sessions.csv` is the durable copy the executor's `clear_awaiting` cannot
    # erase. Both take `checkout_disposition`.
    if renew:
        # ---- STAGE 3 (s3-09): THE FORK. The seam s12-06 left greppable here is DISCHARGED. -----
        # Everything above ran in-pane and is safe in-pane; the renewal is not, so it leaves with a
        # DETACHED process and this one exits. `fork_lifecycle_renewal` stamps the marker first and
        # REFUSES rather than forking blind — its own contract carries the five refusal arms and
        # the denylist argument for the child's environment. NOTHING BELOW MAY ASSUME THE PANE
        # SURVIVES: from the moment the child starts, this pane can be respawned out from under
        # this process at any instant.
        _renew_kind = lifecycle_exec.fork_lifecycle_renewal(
            args, base, me, (row or {}).get("pane", ""))
        if _renew_kind == "daemon-lane":
            print(c(f"next: nothing on your side — a daemon-lane placement request is on disk; "
                    f"the next seed pass relaunches '{me}' caged on this lane. This session is "
                    f"over; do not type another command.", C_HINT))
        else:
            print(c(f"next: nothing on your side — a detached executor is running '{me}'s renewal OUT "
                    f"of this pane and will bring the seat back. This session is over; do not type "
                    f"another command.", C_HINT))
    else:
        # [INTEGRATION POINT — STAGE 3: fork the detached reaper]
        # The done path's twin seam: Stage 3 forks the pane reaper here instead of leaving the
        # debt above for a later human pass.
        #
        # ⚠ THIS LINE NO LONGER TEACHES `close <me> --renew`. Renewal is the SEAT's own act now
        # (`checkout --renew`), so naming leader's close-and-renew as this seat's follow-up would
        # teach the superseded ceremony at the one moment the seat is looking for its next step.
        # ⚠ AND NOTHING IS DISPATCHED FROM HERE. The M4-11 edge fast path stood at this exact line
        # and is DELETED (`one-readiness-predicate`) — the block above `declared_outputs` carries
        # why check-out validates and declares but never dispatches. Do not re-cut this seam.
        # r-checkout-selfclose (owner, 2026-07-31): an `ephemeral: yes` seat's DONE-checkout
        # finishes the way `depart` finishes — after every bookkeeping act above, the CLI kills
        # the seat's own pane, no agent in the path. Run-3 measured the alternative: `depart` was
        # invoked 0 times in 94 launches, every finished seat left its pane as debt, and the reap
        # pass (leader-gated, two-pass, 15-min floor) never drained it — 6 of 10 mapped panes sat
        # finished-but-open, three of them 14-23 h.
        # G-leader-0823-0217-2: the PROCESS leak is the same shape on persistent seats. Checkout
        # records `done`/`incomplete` and used to leave the harness idle forever because only
        # `ephemeral: yes` armed `arm_pid_reaper`. death-stamp confirm-and-reap only runs after an
        # observed death, so a living process never reached it. `cmd_reap --go` is leader-gated and
        # is what failed to drain the 2d11h orphans. Arm the pid+starttime reaper here for EVERY
        # non-renew ending (done, incomplete, unverified). Persistent seats still leave the pane
        # for leader `close-seat` (relay-door); ephemeral still self-kills it.
        _pane_e = (row or {}).get("pane") or detect_pane(None)
        if _pane_e:
            _idents_e = process.pane_harness_idents(_pane_e)
            if _idents_e:
                print(f"arming the exit reaper for harness pid(s) "
                      f"{', '.join(str(p) for p, _ in _idents_e)} — no ghost survives this "
                      f"checkout (it fires only on an exact pid+starttime match, so a "
                      f"recycled pid is safe)")
                process.arm_pid_reaper(_idents_e)
        _seat_e = next((w for w in launch.discover_workers(workers_dir(args)) if w["agent"] == me), None)
        if _seat_e is not None and _seat_e.get("ephemeral"):
            clear_closing(base, me)
            if _pane_e:
                print(f"ephemeral seat, session DONE — killing own pane {_pane_e} (self-close at "
                      f"checkout, r-checkout-selfclose: depart and done-checkout end the same "
                      f"way for ephemeral seats). Goodbye.")
                tmux_kill_pane(_pane_e)
            else:
                print("ephemeral seat, session DONE — no pane to kill (not inside tmux); any "
                      "remnant is leader's close-seat")
            return
        # 7.676: the closing line names the ENDING THAT WAS ACTUALLY RECORDED. Telling a seat that
        # declared itself unfinished "this session is DONE" would hand it, at the last line it ever
        # reads, the very word its check-out just refused to write.
        # D5: the kit-stamped `unverified` path must NOT say "the run records that you said so" —
        # the seat did not say so. That lie is the class of record this gate exists to delete.
        # D32: the discriminant is the FLAG, not a prefix parsed off the seat's reason string.
        if outputs_unverified or incomplete:
            if outputs_unverified:
                print(c(f"next: nothing on your side — this session's `done` was REFUSED "
                        f"(outputs unverified) and the run records `unverified` — the ending "
                        f"whose whole meaning is THIS. You did NOT declare this ending; the kit "
                        f"did, because `done` is a verified claim (D5/D32). Leader frees the pane "
                        f"(`{coord_invocation(args)} close-seat {me}`) and picks the work up; "
                        f"no successor of this seat is booted and NO DAG EDGE ADVANCED on this "
                        f"ending.",
                        C_HINT))
            else:
                if park_on_owner:
                    print(c(f"next: nothing on your side — this session PARKED on the owner's "
                            f"unanswered ask (`blocked-on-human`, disarmed until `ask-answered`). "
                            f"No successor is booted. Do not stay up waiting and do not `--renew`. "
                            f"The wake is the owner's reply in that thread (spec-state-store §2.8).",
                            C_HINT))
                else:
                    print(c(f"next: nothing on your side — this session ended INCOMPLETE and the run "
                            f"records that you said so. Leader frees the pane "
                            f"(`{coord_invocation(args)} close-seat {me}`) and picks the work up; no "
                            f"successor of this seat is booted and NO DAG EDGE ADVANCED on this ending.",
                            C_HINT))
        else:
            print(c(f"next: nothing on your side — this session is DONE and leader frees the pane "
                    f"(`{coord_invocation(args)} close-seat {me}`). Renewing a seat is the SEAT's "
                    f"own act now — `checkout --renew`, before you check out for good.", C_HINT))


def checkout_renew_arm(args, base, me):
    """`checkout --renew` CALL 1: arm the seat's own renewal, teach it call 2, close NOTHING.

    `d-close-renew-decider-recorded` — the SEAT decides its own renew/refresh; no agent stands in
    the execution path and there is no `--force`. That is only safe if the call itself is safe to
    make, so this one does NOT export, does NOT flip the roster row, and records no
    awaiting-close debt (the G-134 debt is the DONE path's, and the record carrying
    `disposition=renew` is written by CALL 2, at the moment something actually closes — s12-07).
    All it does is mute the seat's wakes and print the second call.

    ⚠ THE TWO REFUSALS FIRE BEFORE THE ARMING, NEVER AFTER. A flat-file seat has no folder and so
    no `memory.md` for a handoff to land in, and a `close: mechanical` seat (G-23) is memoryless BY
    RULING. Arming first and refusing second would leave such a seat MUTED for CLOSING_MAX_MIN
    minutes with no renewal path out of it — cut off from the room by the very command that then
    told it no. `s12-06`'s call-2 check stays as a belt-and-braces guard behind this one.

    ⚠ THE CLOSER TOKEN IS THE SEAT'S OWN NAME, never a literal like "self-renew"
    (`r-closing-is-a-true-wake-mute`, s12-01 amendment). `closing_reaches` admits exactly `leader`
    and `entry["closer"]`, and the roster grammar admits ANY non-pipe string as an agent name — so
    a literal token is an unclaimed free key into a narrowed inbox. With the seat's own name the
    admitted set is {leader, me}, and a seat's own sends are never re-served nor woken, so the
    effective inbox is exactly `leader`: what the teaching text below claims.
    """
    seat = next((w for w in launch.discover_workers(workers_dir(args)) if w["agent"] == me), None)
    if seat is not None and seat.get("mechanical_close"):
        refuse(
            "input",
            f"'{me}' declares `close: mechanical` (G-23), so it is memoryless BY DESIGN — no "
            f"memory.md, and therefore no handoff for a successor to read. The owner ruled this "
            f"seat OFF the self-service renew path PERMANENTLY, not provisionally "
            f"(`d-mechanical-no-self-renew`, 2026-07-29). Nothing was armed: your wakes are not "
            f"muted and your session is untouched.\n"
            f"Its renewal is the LEADER-SIDE close-and-relaunch path instead — end this session "
            f"with `{coord_invocation(args)} checkout`, and leader brings the next one up with "
            f"`{coord_invocation(args)} close-seat {me} --renew`.",
            2)
    folder = seat.get("folder") if seat else None
    if folder is None:
        refuse(
            "input",
            f"'{me}' has no seat FOLDER — its descriptor is a flat file, so there is no "
            f"`{me}/memory.md` for a handoff to be written to, and carrying that handoff to your "
            f"successor is the whole point of this path. Nothing was armed: your wakes are not "
            f"muted and your session is untouched.\n"
            f"End this session with `{coord_invocation(args)} checkout` instead; leader relaunches "
            f"the seat if it must come back.",
            2)
    # 7.102: the reason is printed VERBATIM from the boundary, never re-derived here — a second
    # derivation is the skew this row exists to close.
    _mute_ok, _mute_why = set_closing(base, me, me)
    if not _mute_ok:
        print(c(f"WARNING the wake mute could NOT be written ({_mute_why}) — your inbox is NOT "
                f"narrowed and wakes keep arriving. The renewal below is still yours to finish; "
                f"expect interruptions, and tell leader.", C_DEAD), file=sys.stderr)
    # ⚠ VERBATIM (stage-1-2-gate-checkout-spec.md §2.2), WITH ONE AMENDED PARAGRAPH. This text IS
    # the mechanism — it is the CLI teaching the seat the second step, and its wording, its order
    # and its line breaks are the spec's, not this function's. The minute figure is DERIVED from
    # CLOSING_MAX_MIN and never typed: a copy drifts, a reference does not.
    #
    # THE AMENDMENT is the closing paragraph, and it is not a style edit: the spec's text said the
    # note is APPENDED to the seat's memory, and since the owner's 2026-08-03 ruling it REPLACES
    # that file wholesale. Teaching "appended" here would tell a seat its state doc survives, at
    # the exact moment it is deciding what to leave out of the note.
    memory_path = folder / "memory.md"
    print(
        f"renewal armed: {me} — wakes are muted and your inbox is narrowed to leader (clears in "
        f"{CLOSING_MAX_MIN} min\n"
        f"if you do not finish).\n"
        f"\n"
        f"NOTHING IS CLOSED YET. Two things are still yours, in this order:\n"
        f"  1. STOP READING. Do not run `read` again — the log keeps queueing and your successor\n"
        f"     inherits your cursor, so nothing is lost by stopping here.\n"
        f"  2. WRITE YOUR SUCCESSOR'S HANDOFF, then re-run this command with it:\n"
        f"\n"
        f"     coordinate checkout --renew --handoff \"<what the next session of this seat must "
        f"do>\"\n"
        f"     coordinate checkout --renew --handoff-file <path>   (same thing, note read from a "
        f"file)\n"
        f"\n"
        f"Write it for someone with NO memory of this session: what is in flight, what you were "
        f"about\n"
        f"to do next, what you tried and ruled out, and any path or id they would otherwise have "
        f"to\n"
        f"re-derive. IT BECOMES YOUR SEAT MEMORY IN FULL — {memory_path} is REPLACED by it (owner\n"
        f"ruling 2026-08-03: memory.md IS the handoff, nothing else lives in it), and it is "
        f"printed to\n"
        f"your successor at its check-in. Anything already in that file that still matters, carry "
        f"into\n"
        f"the note; what you leave out is gone. Target ~{HANDOFF_MAX_LINES} lines.")
