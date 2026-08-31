# ---------- workers.md ----------

def load_workers(base):
    path = base / "workers.md"
    if not path.exists():
        return path, [], []
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = []
    for i, line in enumerate(lines):
        m = WORKER_ROW.match(line.rstrip("\n"))
        if m and m.group("agent") != "agent":
            d = {k: v.strip() for k, v in m.groupdict().items()}
            d["_line"] = i
            rows.append(d)
    return path, lines, rows


def row_text(r):
    return (f"| {r['agent']} | {r['active']} | {r['pane']} | {r['summary']} "
            f"| {r['checkin']} | {r['checkout']} | {r['lastread']} |\n")


# ---------------------------------------------------------------------------------------------
# ADDRESSABLE NON-MEMBERS — `seats/leader/ruling-addressable-non-member.md`, ruled 2026-07-27.
#
# THE DEFECT. Every source `known_recipients` draws on is PACKAGE-LOCAL by construction: this
# package's roster rows, its seat descriptors, its groups, its relay tokens. That locality is
# deliberate (see `relay_seats`: G-111 is a foreign seat sharing a live roster name). So an agent
# whose descriptor lives in ANOTHER goal folder resolves nowhere, and BOTH gates in `cmd_send`
# close on it: `send <it>` is refused as an unknown recipient (F5), and its own `ask` is refused
# because nobody can answer it (S-7). Measured live at run-2 #509/#510: a meta-agent summoned to
# build seats could neither message the leader nor be messaged, and finished its work through
# `tmux send-keys` — off the bus, so no record, no threading, no delivery confirmation.
#
# ⚠ THE RECIPIENT HALF IS THE WHOLE DEFECT; THE ASK-REFUSAL IS ITS CONSEQUENCE. The S-7 gate asks
# whether the SENDER can be addressed — i.e. whether it is a recipient. Fix recipient resolution
# and the ask-refusal dissolves on its own. They must not be fixed separately.
#
# THE GRANT IS EXACTLY ONE CAPABILITY: A NAME THAT RESOLVES AS A RECIPIENT.
#
#   GRANTED      resolves as a recipient · can be `--re`-linked in ask->answer threading ·
#                carries its `from-pkg:` origin UNCHANGED (nothing is built for that half — the
#                engineer's stage-4 distinguisher already stamps it `external`, and it keeps
#                doing so precisely BECAUSE no roster row is created here).
#   NOT GRANTED  a roster row · a `taskforce.csv` row · A WAKE · a read cursor · broadcast or
#                group membership by default · any count against the pane cap · inclusion in the
#                chief-of-staff's sweep or any close/kill/reap lifecycle · read-everything · any
#                KG `realizes:` edge.
#
# A future reader must not infer any right from this that is not in the GRANTED line.
#
# ⚠⚠ NO ROSTER ROW, AND THIS IS THE CONSTRAINT THAT SHAPES EVERYTHING ELSE. A row would buy the
# name, the cursor and the wake in one move — which is exactly why it is forbidden: it buys them
# by making the agent a member, contradicting the owner ruling that it is not one. It is also the
# repair THIS TOOL'S OWN S-7 REFUSAL TEXT RECOMMENDS ("check in first so you have a roster row"),
# which is how the trap gets found by every next meta-agent; that text is corrected below.
#
# ⚠ DELIVERY IS PULL, NOT PUSH — STATED HERE AND IN THE OUTPUT, NEVER LEFT TO BE DISCOVERED.
# A non-member has no pane in this run's tmux session and no cursor, so `addressable` CANNOT mean
# `woken`. The message is appended to the log addressed to it and THE CORRESPONDENT READS THE LOG
# ITSELF. If that stays implicit, the first person to address one will assume a wake, get silence,
# and read the silence as "considering" rather than "never delivered" — the hazard the correspondent
# named about itself. A dropped relay is undetectable to it, and that does not change because the
# name now resolves.
ADDRESSABLE_COLS = ["descriptor", "admitted-by", "admitted"]


def load_addressable(args):
    """({address: descriptor-path}, [error, ...]) for this package's addressable non-members.

    An ADDRESS is the correspondent's own name, plus every ROLE TOKEN its descriptor declares in
    `relays:` (7.546) — both read from the descriptor, never from the register.

    DERIVED, NEVER A KIT-SIDE NAME LIST (constraint 1). `SPECIAL_CASE_SEATS` was demoted to a
    default table on exactly this ground, and the engineer refused to validate `window:` against
    one run's four hardcoded names on the same one: a shared kit must not carry one campaign's
    furniture. So the register `<package>/addressable.csv` carries ONLY A PATH — it cannot even
    state the name — and the name is read from the descriptor the correspondent itself owns.
    (`taskforce.csv` is the precedent: a run-authored registry this tool only ever reads.)

    TWO-SIDED AND MACHINE-ENFORCED (constraint 2). The package points at a descriptor; the
    descriptor must declare `addressable: non-member`. Either half alone does nothing. A package
    therefore cannot make another goal's seat addressable without that seat having said so, and a
    descriptor that says so is inert until some package points at it.

    FAILS LOUD, NEVER SILENT (constraint 3). Every row that does not resolve — missing file,
    unreadable, no frontmatter, no name, no opt-in, or a name that COLLIDES with a local seat —
    yields an ERROR STRING and admits nothing. Four fail-silent defects landed in this system in
    one evening; a register that quietly dropped a row would be the fifth. The collision refusal is
    G-111 itself: a foreign descriptor named `leader` must never shadow the local one.
    """
    pkg = package_dir(args)
    path = pkg / "addressable.csv"
    header, rows = read_csv_table(path, ADDRESSABLE_COLS)
    if not rows:
        return {}, []
    if "descriptor" not in header:
        return {}, [f"{path}: no `descriptor` column — header is {','.join(header)}"]
    i = header.index("descriptor")
    out, errors = {}, []
    for r in rows:
        raw = (r[i].strip() if i < len(r) else "")
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = (pkg / p)
        try:
            text = p.resolve().read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{raw}: descriptor unreadable ({exc.__class__.__name__}) — admits nothing")
            continue
        if not text.startswith("---"):
            errors.append(f"{raw}: no frontmatter — admits nothing")
            continue
        fm_end = text.find("\n---", 3)
        fm = text[:fm_end] if fm_end != -1 else text
        m = FM_KEY["agent"].search(fm)
        if not m:
            errors.append(f"{raw}: descriptor declares no `seat:`/`agent:` name — admits nothing")
            continue
        name = m.group(1)
        decl = FM_KEY["addressable"].search(fm)
        if not decl or decl.group(1).lower() != "non-member":
            errors.append(f"{raw}: '{name}' does not declare `addressable: non-member` in its own "
                          f"descriptor — a package cannot grant this on another agent's behalf")
            continue
        out[name] = str(p)
        # THE ROLE WORD IS AN ADDRESS TOO (7.546). A correspondent that declares `relays:` beside
        # its opt-in is reachable by that ROLE TOKEN as well as by its name, so a fresh goal's
        # escalation has a legal address before anybody holds the role locally. Admitting only the
        # NAME left the two halves missing each other by one word.
        #
        # ⚠ WHAT THE FERRY CARRIES CHANGED (task 7.614, `decisions.md#d-agents-address-owner-not-
        # master`): agents NEVER INITIATE to `master`. The closed addressing rule is three lines —
        # initiate -> `owner` (the reserved bus token the ferry's agent-thread leg delivers under
        # the two ratified gates), answer -> the asker, else the seat BY NAME. `bus-ferry.js`
        # deleted its role-token constant and the whole `roleHeldLive`/`seatDeclaresRole` roster
        # stand-down at `004eeba`; its live surface is `OWNER_TOKEN`/`addressesOwner`, and a
        # master-addressed row is never owner-bound. The register below is unchanged in
        # mechanism: it still admits a declared role word as an address, and that is still what
        # makes a role-addressed row resolvable locally.
        #
        # BOTH HALVES STILL AGREE, and this is why the read is HERE rather than in a second parse:
        # the token is read off the SAME frontmatter that already proved it accepts outside mail,
        # so a descriptor declaring `relays:` alone grants nothing and a register cannot invent a
        # role word for somebody. The token joins `out` as an ordinary key, so it rides the
        # G-111 local-collision refusal in `addressable_nonmembers` exactly as the name does.
        for tok in (_fm_list(fm, "relays") or []):
            t = tok.lower()
            if out.get(t) == str(p):
                continue      # the correspondent's own name — already admitted, nothing to add
            if t in out:
                # FAILS LOUD (constraint 3). Two correspondents claiming one role word is an
                # ambiguity, and the register's ORDER settles it: the earlier grant stands and the
                # later one is refused IN WRITING. Silently overwriting would re-point an
                # escalation at a terminus the sender never chose, with nothing on disk saying so.
                errors.append(f"{raw}: '{name}' declares `relays: {t}`, but that address is "
                              f"already admitted by an EARLIER register row — refused; the "
                              f"earlier grant stands and this one adds nothing")
                continue
            out[t] = str(p)
    return out, errors


def addressable_nonmembers(args, base):
    """Addresses admitted after the LOCAL-COLLISION check, plus every error to report.

    Split from `load_addressable` because the collision test needs this package's local names,
    and a resolver that reached for them would make the register's own parse depend on roster
    state. Local always wins: a foreign descriptor never shadows a seat of this run.

    ⚠ A DECLARED ROLE TOKEN IS AN ADDRESS AND RIDES THIS SAME REFUSAL (7.546) — it is a key of
    `found` like any name, so a correspondent declaring `relays: leader` in a run that HAS a
    `leader` seat is refused that word and stays reachable by its own name. Local wins for the
    token for the same reason it wins for the name: G-111 is about the address, not its origin."""
    found, errors = load_addressable(args)
    _, _, rows = load_workers(base)
    local = {r["agent"] for r in rows} | set(briefing_frontmatters(workers_dir(args))) \
        | set(group_map(base)) | {"all"}
    admitted = {}
    for name, p in found.items():
        if name in local:
            errors.append(f"{p}: '{name}' COLLIDES with a seat of this package — refused, the "
                          f"local name wins (G-111: a foreign seat sharing a live roster name "
                          f"must never be resolved here)")
            continue
        admitted[name] = p
    return admitted, errors


def report_addressable_errors(args, base, stream=None):
    """Print every unresolved register row. Constraint 3 — REFUSE VISIBLY, never degrade to a
    silent success. Called on the paths where a name is resolved, so a broken row surfaces at the
    moment someone is relying on it rather than at some later audit nobody runs."""
    _, errors = addressable_nonmembers(args, base)
    for e in errors:
        print(f"warning: addressable.csv — {e}", file=stream or sys.stderr)
    return errors


def current_row(rows, agent):
    """Latest row for an agent (last check-in wins). P1 keeps at most one active."""
    mine = [r for r in rows if r["agent"] == agent]
    return mine[-1] if mine else None


def update_row(base, agent, mutate):
    """Locked read-modify-write of ONE roster row: re-reads workers.md under the lock (so a
    concurrent writer's rows are never clobbered by a stale in-memory copy), applies `mutate`
    to the agent's current row, writes. `mutate` returning False means "no change, skip the
    write". Returns (ok, note)."""
    with coord_lock(base):
        path, lines, rows = load_workers(base)
        row = current_row(rows, agent)
        if row is None:
            return False, f"no roster row for '{agent}'"
        if mutate(row) is False:
            return True, "unchanged"
        lines[row["_line"]] = row_text(row)
        atomic_write(path, "".join(lines))
    return True, ""


# ---- owner state (task 7.85, owner ruling r-owner-state-is-not-binary) --------------------
# THE STATES ARE ESCALATION POLICIES, NOT FACTS ABOUT THE HUMAN. That is why a third VALUE is
# right and a second FIELD is wrong: `present` and `afk` never meant "at the desk"/"away", they
# meant "escalate now"/"queue them". `reachable` is the third policy — escalate BY LAUNCHING THE
# DOOR — and the owner ruled it a first-class state of the system, not a run's convention.
#
# ⚠ THIS TABLE IS THE SINGLE HOME. `choices=`, the `--help` text, and what every consumer RENDERS
# are all derived from it, so none of them can drift from the others or from behaviour. The
# ESCALATION ACT lives here, in code — NOT in the free-text note. That is the whole point of the
# row: before this, the third state existed only when someone wrote a good note, and two seats
# reconstructed it in prose on the same afternoon (the leader set `present` at 16:5x and then
# qualified it away in ~400 characters; the chief-of-staff relayed an order built on the same
# distinction). Prose does not survive a rewrite. Delete every note and the distinction still stands.
#
# ⚠⚠ THE ACT IS A FUNCTION OF THE WORLD AT RENDER TIME, NOT OF THE STATE TOKEN ALONE (task 7.89,
# `G-269`). It was static text for about forty minutes and went stale BY BEING OBEYED: `reachable`
# told every seat to LAUNCH THE DOOR, someone did, and the instruction stayed up — true when the
# state was set, false the moment it was carried out. ⇒ THE SURFACE WAS MOST WRONG EXACTLY WHEN THE
# ROOM HAD BEEN MOST RESPONSIVE, which is the worst possible correlation for an escalation
# instruction. `reachable` still describes the OWNER correctly; only the run-side ACT decayed, so
# this needs no fourth state and no new field — just a world the act is composed against.
OWNER_STATES = {
    "present": (
        "rulings can be escalated NOW",
        lambda w: (
            f"message the owner directly — the door ({w['door']}) is up and receiving"
            if w["door_active"] else
            "⚠ state says PRESENT but NO door session is running — nothing is receiving. "
            "Launch the door, or correct the state; do not assume a message lands"
        ),
    ),
    "reachable": (
        "at the PC, AFK FROM THE RUN — no master session running, a pane standing where one can be",
        lambda w: (
            f"the door is ALREADY UP ({w['door']}) — just MESSAGE it. No launch needed"
            if w["door_active"] else
            "LAUNCH THE DOOR — relaunch the seat that carries the owner relay in the standing pane "
            "(resolve the pane from `workers`, never a remembered %n), then message it"
        ),
    ),
    # ⚠ CHECKED UNDER THE SAME LENS AND NOT STALE (criterion 2): `afk`'s act is the NULL act, and a
    # null act cannot go stale by being obeyed — there is nothing to carry out that would falsify
    # it. Deliberately left unconditional rather than gated for symmetry's sake.
    "afk": (
        "queue rulings; do NOT page",
        lambda w: "none until the owner returns — anything urgent waits",
    ),
}


def owner_world(args, base):
    """The facts an escalation act is composed against. READ-ONLY, and that is criterion 4.

    ⚠⚠ IT NEVER TOUCHES A PANE, NEVER LAUNCHES, NEVER PROBES THE DOOR. The question "does a
    relaunch work?" is DESIGNED OUT rather than answered — `bars.md` 4 says a pane whose purpose is
    human contact is never reaped, and testing a relaunch against the live door is that same
    hazard one step earlier. This reads two files.

    The door is derived from `relays:` in the seat descriptors — NEVER a kit-side name list, the
    same derivation the reap exemption uses, and for the reason stated there: a name list freezes
    one campaign's roles into a shared tool and the next such seat is forgotten identically.
    """
    door, active = None, False
    try:
        decls = inbox_decls(args)
    except Exception:  # noqa: BLE001 — a bad descriptor must never break `status`
        decls = {}
    for seat, d in sorted((decls or {}).items()):
        if (d or {}).get("relays"):
            door = seat
            break
    if door:
        try:
            _p, _l, rows = load_workers(base)
            row = current_row(rows, door)
            active = bool(row and row.get("active") == "yes")
        except Exception:  # noqa: BLE001
            active = False
    return {"door": door or "the owner-relay seat", "door_active": active}
OWNER_STATE_UNKNOWN = (
    "no owner state has been recorded",
    "none defined — run `owner <state>` before relying on this",
)


def owner_status(base):
    """Parse `owner-status.md` into STRUCTURE — state, since, note — never one opaque string.

    ⚠ IT USED TO RETURN THE WHOLE LINE AFTER `owner:`, and both consumers printed that raw. So the
    enum value and the operator's free text were literally the same field to every reader, and a
    third state would have rendered identically to the other two no matter what the enum accepted.
    Splitting them is what makes the state itself renderable, which is criterion 5 of task 7.85.

    BACK-COMPAT IS REQUIRED, NOT BEST-EFFORT: a file written before this change must still read
    correctly (its state token is already the first word after `owner:`), and an UNRECOGNISED state
    — hand-edited, or from a newer writer — degrades honestly: it is reported as the state it says,
    marked unknown, with the raw line preserved. Vanishing would be worse than being wrong.
    """
    raw, state, since, note = "", "unknown", "", ""
    path = base / "owner-status.md"
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.startswith("owner:"):
                raw = ln[len("owner:"):].strip()
                break
    if raw:
        head, sep, tail = raw.partition("|")
        state = head.strip() or "unknown"
        rest = tail.strip() if sep else ""
        # The writer's shape is `since {ts}[ — {note}]`. The note delimiter is an EM DASH, which
        # is also legal inside a note; partition on the FIRST one, which is the writer's.
        if rest.startswith("since"):
            rest = rest[len("since"):].strip()
        since, _, note = (p.strip() for p in rest.partition("—"))
    return {
        "state": state,
        "since": since,
        "note": note,
        "raw": raw,
        "known": state in OWNER_STATES,
    }


def owner_escalation(state, world):
    """The act for `state` composed against `world` — the ONE place an act is produced.

    ⚠ CRITERION 5: the conditional lives HERE, where the act is composed, never in a note a human
    writes. A note-borne condition is exactly the defect 7.85 existed to end, and its own follow-up
    must not reintroduce it.
    """
    entry = OWNER_STATES.get(state)
    act = entry[1] if entry else OWNER_STATE_UNKNOWN[1]
    return act(world) if callable(act) else act


def print_owner_status(base, label_width=7, args=None):
    """Render owner state for a consumer. ONE renderer, called by BOTH `status` and `workers`.

    Two consumers rendering this by hand is how the distinction collapsed in the first place, so
    they share this function rather than each formatting the dict. The MEANING and the ESCALATION
    ACT come from OWNER_STATES — from code — and the operator note is printed separately and
    subordinate, so it can be empty without the state becoming ambiguous.
    """
    st = owner_status(base)
    meaning = OWNER_STATES.get(st["state"], OWNER_STATE_UNKNOWN)[0]
    act = owner_escalation(st["state"], owner_world(args, base))
    tone = C_ALIVE if st["state"] == "present" else (C_LABEL if st["known"] else C_DEAD)
    head = c("owner:".ljust(label_width), C_LABEL)
    since = f" | since {st['since']}" if st["since"] else ""
    unknown = "" if st["known"] else "  (UNRECOGNISED STATE — reported verbatim, not translated)"
    pad = " " * (label_width + 1)
    print(f"{head} {c(st['state'], tone)}{since}{unknown}")
    print(f"{pad}{meaning}")
    print(f"{pad}escalation: {act}")
    if st["note"]:
        print(f"{pad}note (operator, not the carrier): {st['note']}")


def cmd_owner(args):
    # P15 — workers were inferring owner availability and getting it wrong; state it explicitly.
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — any resolved identity may set it.
    gate(args, "owner")
    base = base_dir(args)
    base.mkdir(parents=True, exist_ok=True)
    note = f" — {args.note}" if args.note else ""
    with coord_lock(base):
        atomic_write(base / "owner-status.md",
                     "# owner-status — script-managed (coord.py owner "
                     f"<{'|'.join(OWNER_STATES)}>)\n"
                     f"owner: {args.state} | since {now()}{note}\n")
    print(f"owner is now: {args.state}{note}")
    # Echo the MEANING and the ESCALATION ACT back at the setter, from the same table every reader
    # renders. The leader set `present` at 16:5x and then spent a long note explaining that it did
    # NOT mean "escalate now" — a setter shown what the value it just wrote will TELL EVERY READER
    # is a setter given the chance to notice it picked the wrong one (task 7.85, criterion 3).
    _meaning = OWNER_STATES.get(args.state, OWNER_STATE_UNKNOWN)[0]
    print(f"  means:      {_meaning}")
    print(f"  escalation: {owner_escalation(args.state, owner_world(args, base))}")
    # G-181: this used to coach `send all "owner is ..." --type note`, which the tool REFUSES
    # twice over (positional body, then `a note is never an all broadcast`). Adding --inline would
    # have silenced a substring check while the command stayed refused. But the deeper reason not
    # to restore it in any form is DIVERGENCE, not the refusal: the line above just wrote the
    # MACHINE surface, and a hand-typed second statement of owner presence is a copy that can
    # disagree with it. `owner: unknown` sat on the roster through hours of explicit AFK posture
    # precisely because presence was being restated by hand instead of read from one home.
    print(c(f"next: nothing to send — {coord_invocation(args)} status and workers now report "
            f"this to every seat that asks, from the surface just written (P15)", C_HINT))


def truncate(text, limit=DIGEST_SNIPPET):
    """One-line snippet. Newlines are collapsed: every caller renders ONE line per row, and a
    body with embedded newlines would silently break that row into several."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def state_agent_types(base):
    """{seat: agent_type} straight off `state.json`'s own snapshot (task 7.80's `coordinate`
    half, G-195) — never re-derived, never a second source. `teamview` reads the identical
    field the identical way (`teamview.py:agent_type_bit`); this is the same property read a
    second time, not a second classification.

    Returns {} on anything short of a clean snapshot — missing file, unparseable, wrong shape,
    or a pre-7.80 snapshot with no such key on any row — so `workers` degrades to its
    pre-7.80 rendering rather than raising or inventing a value (`load_state_snapshot`'s own
    fail-safe: never raises, this caller's fail-safe direction is an empty dict).

    ⚠⚠ DISPLAY ONLY, NEVER A GATE. This field is a SENSOR OBSERVATION of a descriptor's
    declared claim, not an authorization — the identity gate (`resolve_agent`/`gate`) is the
    only authorization, and nothing may ever branch on this dict's values
    (`r-agent-type-field-name`'s binding condition, restated here because this is now a fourth
    site that touches the field)."""
    snap = load_state_snapshot(base)
    if snap is None:
        return {}
    out = {}
    for s in snap.get("seats") or []:
        if not isinstance(s, dict):
            continue
        seat, atype = (s.get("seat") or "").strip(), (s.get("agent_type") or "").strip()
        if seat and atype:
            out[seat] = atype
    return out


def cmd_workers(args):
    """Who is alive, at a glance (T2/F4). DEFAULT is one CURRENT row per agent with truncated
    summaries and an unread-lag column; --full keeps summaries whole, --history replays every
    historical row (the pre-T2 behavior)."""
    base = base_dir(args)
    _, _, rows = load_workers(base)
    nonmembers, addr_errors = addressable_nonmembers(args, base)
    print_owner_status(base, label_width=6, args=args)
    # Listed SEPARATELY from the roster, never merged into it: these are not seats, hold no row,
    # and must never be counted in a census, a cap or a sweep. Shown at all because a name that
    # resolves invisibly is its own kind of fail-silent — and the errors are shown for the same
    # reason the successes are.
    if nonmembers or addr_errors:
        print(f"{c('addressable non-members (no row, no wake, no cursor — PULL delivery):', C_LABEL)}")
        for nm in sorted(nonmembers):
            print(f"  {nm} -> {nonmembers[nm]}")
        for e in addr_errors:
            print(c(f"  UNRESOLVED: {e}", C_DEAD))
    if not rows:
        print("no workers registered")
        print(c(f"next: {coord_invocation(args)} launch — nobody has checked in yet", C_HINT))
        return
    _, blocks = load_messages(base)
    tail = blocks[-1]["num"] if blocks else 0
    # Parsed ONCE for the whole listing, then handed to unread_for per row (the lag column is
    # the same exact per-agent unread count `status` reports — see unread_for).
    gmap = group_map(base)
    observers, _ = observer_sets(args)
    live = live_panes()
    # ⚠ THE ROSTER'S LIVENESS COLUMN IS THE REGISTRY'S, NOT THE PANE'S [T4-R8, spec-supervisor §6].
    # `live` above stays, and stays a VIEWPORT enumeration: it answers only whether a wake can be
    # delivered. One probe for the whole goal rather than one per row — a roster render used to be
    # the reason a per-seat liveness call was unaffordable, which is how the pane became the answer.
    _pkg = base.parent if base.name == "coordination" else base
    sittings = liveness.goal_liveness(_pkg)
    agent_types = state_agent_types(base)  # task 7.80's `coordinate` half, G-195
    if getattr(args, "history", False):
        shown = rows
    else:
        shown = [current_row(rows, a) for a in dict.fromkeys(r["agent"] for r in rows)]
    dead = 0
    for r in shown:
        if r["active"] == "yes":
            status, tone = "ACTIVE", C_ALIVE
            _alive = (sittings.get(r["agent"]) or {}).get("alive")
            if _alive is False:
                # The REGISTRY says the process is gone: pid + /proc start-time, the one liveness
                # surface. This is a claim about the SITTING and it is now safe to make.
                status, tone = "DEAD", C_DEAD
                dead += 1
            elif _alive is None and is_tmux_pane(r["pane"]) and live and r["pane"] not in live:
                # No registry row — the sitting is UNSUPERVISED (born outside the daemon and not
                # yet checked in), so nothing here knows whether it is running. The pane says only
                # that a WAKE CANNOT REACH IT, and that is exactly what is reported: never `DEAD`,
                # because absence of a row has never been evidence of death (C-15).
                status, tone = "UNREACHABLE", C_DEAD
        else:
            status, tone = "done", C_DONE
        cursor = f" read@{r['lastread']}" if r["lastread"] not in ("", "0") else ""
        lag = ""
        if r["active"] == "yes" and tail:
            start = int(r["lastread"]) if r["lastread"].isdigit() else 0
            behind = len(unread_for(args, base, r["agent"], start, blocks, gmap, observers))
            lag = f" lag={behind}"
        summary = r["summary"] if getattr(args, "full", False) else truncate(r["summary"])
        # Columns are padded BEFORE colouring: an escape sequence inside a padded field counts
        # toward its width and would shear every column to its right.
        name_col = "{:<16}".format(r["agent"])
        state_col = "{:<7}".format(status)
        pane_col = "{:<6}".format(r["pane"] or "-")
        # `agent_type` (task 7.80/G-195): shown exactly as the snapshot carries it, including
        # "unclassified" — that value is a real, loud OBSERVATION (never silently defaulted),
        # not a gap to hide. Omitted only when the seat has no state.json row at all (pre-7.80
        # snapshot, or team-monitor has not captured this seat yet) — never invented.
        atype = agent_types.get(r["agent"], "")
        atype_bit = f" {c('[' + atype + ']', C_HINT)}" if atype else ""
        print(f"{c(name_col, C_LABEL)} {c(state_col, tone)} pane={pane_col}{atype_bit}{cursor}{lag} {summary}"
              f"  (in {r['checkin']}{', out ' + r['checkout'] if r['checkout'] else ''})")
    _und = undelivered_line(base)
    if _und:
        print(c(_und, C_DEAD))
    # s3-04: the lifecycle marker's READ SIDE, beside the undelivered line and for its exact
    # reason — s3-03 records every out-of-pane renewal and, until Stage 4 lands, nothing looks at
    # it. Rendered on BOTH surfaces the run actually reads (`workers` here, `status` at the twin
    # site), in the same `C_DEAD` — a new colour would say "a different KIND of alarm", which this
    # is not.
    _lcl = lifecycle_exec.lifecycle_line(base)
    if _lcl:
        print(c(_lcl, C_DEAD))
    # G-134: the debt is surfaced HERE because a record nobody reads is not a fix, and the roster
    # is where leader already looks to decide lifecycle. Rendered oldest-first with the pane's LIVE
    # state, because the two debts differ in what they cost: a live pane is still holding memory
    # against the launch floor, a dead one is only an incomplete record. Both still owe a
    # `close-seat` — the roster and session trace are not finished until it runs.
    for seat, entry, age, alive in awaiting_debts(base, live):
        aged = f"{age}min" if age is not None else "unknown age"
        if alive:
            print(c(f"awaiting close: {seat} — its ending is stamped {aged} ago and its PROCESS "
                    f"(pid {entry.get('pid') or '?'}) IS STILL RUNNING, holding memory against the "
                    f"launch floor — the reap did not complete "
                    f"— {coord_invocation(args)} close-seat {seat}", C_DEAD))
        else:
            print(c(f"awaiting close: {seat} — its ending is stamped {aged} ago and its process is "
                    f"already gone, but the registry row is still there, so the roster and session "
                    f"trace are unfinished "
                    f"— {coord_invocation(args)} close-seat {seat} --no-export", C_HINT))
    if not getattr(args, "history", False):
        print(c(f"-- current rows only (log tail #{tail}); --history for every row, --full for "
                f"untruncated summaries", C_HINT))
    if dead:
        print(c(f"next: {dead} row(s) name a sitting the supervisor registry says is GONE — "
                f"{coord_invocation(args)} close-seat <agent> cleans one up", C_HINT))


# ---------- groups.md ----------

def load_groups(base):
    path = base / "groups.md"
    if not path.exists():
        return path, [], []
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = []
    for i, line in enumerate(lines):
        m = GROUP_ROW.match(line.rstrip("\n"))
        if m and m.group("group") != "group":
            rows.append({
                "group": m.group("group").strip(),
                "members": [x.strip() for x in m.group("members").split(",") if x.strip()],
                "by": m.group("by").strip(),
                "created": m.group("created").strip(),
                "_line": i,
            })
    return path, lines, rows


def group_map(base):
    _, _, rows = load_groups(base)
    return {r["group"]: r["members"] for r in rows}


def refuse_special_case_members(args, command, names):
    """G-32 — a SPECIAL-CASE seat is not a group member (owner-spotted: "why was it included in a
    group? it should not"). A group is the room's cheap channel, and the room's conversation is
    exactly what G-20 cut from these seats at the front door; letting them be added walks the same
    traffic in the side one. Enforced in the two commands that can CREATE a membership, because the
    run makes a fresh group per wave and a rule kept only by remembering is the class this run has
    been paying for all night. `--force` stays the single deliberate override, as on every other
    refusal here — and even then delivery is filtered by TYPE (`addressed_to`), so the override
    buys membership, never the traffic."""
    blocked = sorted({n for n in names if broadcast_scope(n) is not None})
    if not blocked:
        return
    many = len(blocked) > 1
    if getattr(args, "force", False):
        print(f"note: `{command}` added special-case seat(s) {', '.join(blocked)} with --force "
              f"(G-32); group messages still reach them only by TYPE", file=sys.stderr)
        return
    refuse(
        "state",
        f"{', '.join(blocked)} "
        f"{'are special-case seats' if many else 'is a special-case seat'} — group traffic is "
        f"not {'their' if many else 'its'} input (G-32). A closer and `engineer` "
        f"serve the SYSTEM or the ROOM, not the goal's conversation, so the room's threads only "
        f"spend the context {'their' if many else 'its'} one job needs.\n"
        f"Send {'them' if many else 'it'} a DIRECT message instead — direct addressability is "
        f"untouched: {coord_invocation(args)} send {blocked[0]} \"<what you need>\" --type note --inline\n"
        f"--force adds {'them' if many else 'it'} anyway, if the membership is deliberate.",
        1)


def cmd_create_group(args):
    base = base_dir(args)
    me = resolve_agent(args)
    _, _, wrows = load_workers(base)
    agent_names = {r["agent"] for r in wrows}
    name = args.group
    if name == "all" or name in agent_names:
        refuse(
            "state",
            f"'{name}' is already a recipient name ('all', or an agent on the roster), "
            f"and `send {name}` could then mean two different things.\n"
            f"Name the group after the WORKSTREAM instead (e.g. views-render).",
            1)
    members = sorted(set(args.members) | {me, "leader"})
    refuse_special_case_members(args, "create-group", members)
    with coord_lock(base):
        path, _, grows = load_groups(base)
        if any(g["group"] == name for g in grows):
            refuse(
                "state",
                f"group '{name}' already exists — creating it again would fork the "
                f"thread.\nAdd people to the existing one instead (leader): "
                f"{coord_invocation(args)} add-to-group {name} <member ...>",
                1)
        if not path.exists():
            atomic_write(path, GROUPS_HEADER)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"| {name} | {', '.join(members)} | {me} | {now()} |\n")
    print(f"group created: {name} — members: {', '.join(members)}")
    print(c(f"next: {coord_invocation(args)} send {name} \"<why this group exists>\" --type note --inline "
            f"— a group nobody was told about carries no thread", C_HINT))


def cmd_add_to_group(args):
    gate(args, "add-to-group")
    # Only the names being ADDED are policed: a group that already carries a special-case seat
    # (three did when G-32 was filed) must stay editable, or the refusal would block its own fix.
    refuse_special_case_members(args, "add-to-group", args.members)
    base = base_dir(args)
    with coord_lock(base):
        path, lines, grows = load_groups(base)
        row = next((g for g in grows if g["group"] == args.group), None)
        if not row:
            known = ", ".join(sorted(g["group"] for g in grows)) or "(none yet)"
            refuse(
                "state",
                f"there is no group '{args.group}', so there is nothing to add to.\n"
                f"existing groups: {known}\nCreate it instead: {coord_invocation(args)} "
                f"create-group {args.group} <member ...>",
                1)
        members = sorted(set(row["members"]) | set(args.members))
        lines[row["_line"]] = f"| {row['group']} | {', '.join(members)} | {row['by']} | {row['created']} |\n"
        atomic_write(path, "".join(lines))
    print(f"group {args.group} members: {', '.join(members)}")
    print(c(f"next: {coord_invocation(args)} send {args.group} \"<who joined, and why>\" "
            f"--type note --inline", C_HINT))


def cmd_remove_from_group(args):
    """(leader) Drop members from an existing group — add-to-group's missing half, and the ONLY
    sanctioned way to undo a membership: `coordination/` is script-managed and hand-editing it is
    banned, so before this command a wrong member could be added but never taken back. G-32 is the
    case that needed it: three groups carried the watcher from before the special-case cut landed,
    and `create-group` refuses a re-create."""
    gate(args, "remove-from-group")
    base = base_dir(args)
    with coord_lock(base):
        path, lines, grows = load_groups(base)
        row = next((g for g in grows if g["group"] == args.group), None)
        if not row:
            known = ", ".join(sorted(g["group"] for g in grows)) or "(none yet)"
            refuse(
                "state",
                f"there is no group '{args.group}', so there is nothing to remove "
                f"from.\nexisting groups: {known}",
                1)
        absent = [m for m in args.members if m not in row["members"]]
        if absent and not getattr(args, "force", False):
            refuse(
                "state",
                f"{', '.join(absent)} "
                f"{'are' if len(absent) > 1 else 'is'} not in group '{args.group}', so removing "
                f"{'them' if len(absent) > 1 else 'it'} would report a change that did not "
                f"happen.\ncurrent members: {', '.join(row['members']) or '(none)'}\n"
                f"--force drops the names that ARE members and ignores the rest.",
                1)
        members = [m for m in row["members"] if m not in set(args.members)]
        lines[row["_line"]] = f"| {row['group']} | {', '.join(members)} | {row['by']} | {row['created']} |\n"
        atomic_write(path, "".join(lines))
    print(f"group {args.group} members: {', '.join(members) or '(none)'}")
    print(c(f"next: {coord_invocation(args)} send {args.group} \"<who left, and why>\" "
            f"--type note --inline", C_HINT))


# ---------- messages.md ----------

def load_messages(base):
    path = base / "messages.md"
    if not path.exists():
        return path, []
    blocks, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = MSG_HEADER.match(line)
        if m:
            current = {"num": int(m.group("num")), "sender": m.group("sender"),
                       # None = written from INSIDE this package, which is every message in every
                       # log predating this field. Only a foreign sender carries an origin.
                       "origin": m.group("from_pkg"),
                       "to": m.group("to"), "type": m.group("type"),
                       "supersedes": int(m.group("supersedes")) if m.group("supersedes") else None,
                       "re": int(m.group("re")) if m.group("re") else None,
                       # None = written before the execution stamp existed (design-lock item 5).
                       "exec": m.group("exec_id"),
                       # W4's three. None on every row written before they existed, which is the
                       # honest reading — `milestone_of` is where the pre-W4 `why:` fallback lives.
                       "milestone": m.group("milestone"),
                       "chat_thread": m.group("chat_thread"),
                       "deliver": m.group("deliver"),
                       # The approval mark (2026-08-27). None on every ordinary row — only the
                       # plan-verifier's approval ask carries it, and only the ferry reads it.
                       "approve_commit": m.group("approve_commit"),
                       "why": (m.group("why") or "").strip() or None,
                       "ts": m.group("ts").strip(),
                       "lines": [line]}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(line)
    return path, blocks


def next_message_number(blocks):
    return max((b["num"] for b in blocks), default=0) + 1


def _append_message_unlocked(base, sender, to, mtype, body, supersedes=None, re_num=None,
                             why=None, origin=None, milestone=None, chat_thread=None,
                             deliver=None, approve_commit=None):
    """The append WITHOUT the lock — for callers already inside a `coord_lock` hold
    (`escalate_if_second_fail` derives + scans + appends under ONE hold; a nested
    `coord_lock` on a second fd of the same .lock file would deadlock under flock).
    Everyone else calls `append_message`.

    ⚠ THE TYPE IS VALIDATED HERE, NOT AT ARGPARSE (adv, C40, and the choke-point rule). This
    docstring used to say the function "validates nothing" and `escalate_if_second_fail` was cited
    as proof that a wrapper-level check is unreachable: it writes through this function from inside
    the lock and cannot call `append_message`. argparse `choices=` covers exactly one caller — the
    `send` verb — and every internal writer (verdict, escalation, finish edge, the closer) walks
    past it. So the closed vocabulary is enforced at the TRUE SINGLE WRITER, and `append_message`
    inherits it.

    ⚠ THIS DOES NOT REACH A HAND-EDITED LOG, and that limit is measured rather than assumed
    (adv, C44). The two stray `type: correction` rows on build-core-daemon-mvp/run-3
    (`messages.md` #6027, #6028, 2026-08-09) were NOT written by a bypassing writer: their
    `from:` fields carry parenthetical prose ("w7573-docs-correction (conductor-dispatched, task
    7.573)"), which no caller of this function can produce — `sender` comes from `resolve_agent`
    as a bare token. They were typed into the file by an agent editing `messages.md` directly. A
    consequence worth stating: those two rows do not match `MSG_HEADER` (`sender` is `\\S+`), so
    they parse as BODY of the preceding block and are invisible to every reader in this file. The
    route is closed by the rule that a seat never hand-writes the log — never by a check here."""
    if mtype not in MESSAGE_TYPES:
        raise ValueError(
            f"message type {mtype!r} is not in the closed vocabulary "
            f"({', '.join(MESSAGE_TYPES)}). The log is append-only, so a row typed with a word no "
            f"reader knows is permanent residue that every type filter silently skips.")
    if mtype in WRITER_HELD_TYPES:
        raise ValueError(
            f"message type {mtype!r} is a known type with NO CONSUMER YET, so this file refuses to "
            f"write one: the row would sit forever in an append-only log waiting for a reader that "
            f"does not exist. It is admitted at every door (enum, gateway, store) so that the "
            f"package which builds its consumer only has to remove it from WRITER_HELD_TYPES.")
    path, blocks = load_messages(base)
    n = next_message_number(blocks)
    if not path.exists():
        path.write_text(MESSAGES_HEADER, encoding="utf-8")
    # G-94: a sender writing into a package it is not rostered in NAMES WHERE IT CAME FROM.
    # Written only for a foreign sender, so a local send's header is byte-identical to before.
    org = f" | from-pkg: {origin}" if origin else ""
    sup = f" | supersedes: {supersedes}" if supersedes is not None else ""
    rel = f" | re: {re_num}" if re_num is not None else ""
    # #198: the clause rides IN THE LOG LINE, not just in the sender's terminal — a reader
    # judging whether a broadcast earned everyone's attention can see the claim it made.
    wc = f" | why: {why}" if why else ""
    # THE EXECUTION STAMP RIDES EVERY ROW (design-lock item 5). The file stays SINGLE and
    # append-only — the stamp is what scopes a read to one execution, so successive executions of
    # one goal are separable without a second file and without a second numbering space.
    #
    # ⚠ THE NUMBER ITSELF IS STILL ALLOCATED ACROSS THE WHOLE FILE, and that is a deliberate
    # divergence from a literal reading of "numbering scopes by stamp" — disclosed rather than
    # taken silently. Restarting at 1 per execution would put two rows numbered `5` in one
    # append-only log, and `supersedes:`/`re:`/every cursor in this file addresses a row by its
    # NUMBER ALONE; they would all become ambiguous. The collision item 5 names is already
    # impossible here for a stronger reason: ONE file, ONE lock, one max — two leaders cannot
    # claim one id when there is only one allocator. The stamp gives the SCOPE; the number keeps
    # its uniqueness.
    ex = f" | exec: {current_execution(base)}"
    # W4's three, emitted in the grammar's order and all BEFORE `why:` (adv, C41/C42) — `why` is
    # the last labelled field by construction, and anything after it is eaten by its `[^|]*?`.
    ms = f" | milestone: {milestone}" if milestone else ""
    ct = f" | chat-thread: {chat_thread}" if chat_thread else ""
    dv = f" | deliver: {deliver}" if deliver else ""
    # THE APPROVAL MARK, and it is a HEADER KEY for the reason `milestone:` became one (adv, C41):
    # the ferry has to tell an approval ask from an ordinary owner question BEFORE it posts, and a
    # sigil pattern-matched out of a free-text digest would be a second authority over an
    # irreversible door. Its authority is checked once, at `cmd_send` — see the gate there.
    ac = f" | approve-commit: {approve_commit}" if approve_commit else ""
    block = (f"\n## {n} | from: {sender}{org} | to: {to} | type: {mtype}{sup}{rel}{ex}"
             f"{ms}{ct}{dv}{ac}{wc} | "
             f"{now()}\n"
             f"\n{body}\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(block)
    return n


def append_message(base, sender, to, mtype, body, supersedes=None, re_num=None, why=None,
                   origin=None, milestone=None, chat_thread=None, deliver=None,
                   approve_commit=None):
    """Allocate the next message number AND append the block inside one lock hold — two
    concurrent sends used to read the same tail and claim the same ID (run-obs §589).
    Returns the number. Type validation is INHERITED from `_append_message_unlocked`, never
    restated here (the choke-point rule: one writer, one set of send-time invariants)."""
    with coord_lock(base):
        return _append_message_unlocked(base, sender, to, mtype, body, supersedes=supersedes,
                                        re_num=re_num, why=why, origin=origin,
                                        milestone=milestone, chat_thread=chat_thread,
                                        deliver=deliver, approve_commit=approve_commit)


# ---- dod-judge two-strikes derivation (7.581 / Q17) --------------------------------------------
#
# The consecutive-FAIL count for a milestone is DERIVED from this log at the instant of the call,
# NEVER stored — no counter, no retry/attempt column, no status field anywhere (Rule 14: a stored
# count is a second ledger that drifts silently and keeps answering). A PASS resets the count BY
# CONSTRUCTION: the count is the length of the TRAILING run of FAIL trial verdicts, so there is
# no reset step to forget and nothing to lose across a daemon restart or a seat renewal.

# A trial verdict's body opens with exactly `verdict: PASS` or `verdict: FAIL` (the dod-judge
# seat's contract); anything else never extends a FAIL run.
VERDICT_CLAUSE = re.compile(r"^verdict:\s*(PASS|FAIL)\b", re.IGNORECASE | re.MULTILINE)
# The escalation record's first body line — what makes it findable (idempotency scan) and what
# excludes it from the trial walk. It is a record ABOUT trials, not a trial.
#
# ⚠ The word "second" survives the bar becoming configurable ON PURPOSE. This is a MACHINE MARKER,
# not prose: it is the appended row's identity, and the at-most-once scan finds an escalation that
# landed on an earlier invocation by matching it. Rename it and every escalation row already in a
# live log goes invisible to the scan, which appends a second one. The human-readable line beneath
# it names the resolved bar.
ESCALATION_MARKER = "escalation: second-consecutive-FAIL"


def _escalation_key(text):
    """W8 (adv, C77) — an escalation's DEDUP KEY: its first non-empty body line, normalized.

    The judge family's key is `ESCALATION_MARKER`, which IS a first body line; this generalizes
    that one pattern to the leader's own rows rather than adding a second. Normalization is
    case-folding plus whitespace collapse and nothing else — a key that survived rewrapping but
    not a re-typed capital letter would fail exactly when a re-woken sitting re-composes its own
    words, which is the case it exists for. `""` when the body opens with nothing (refused by the
    caller: a key nothing can equal would make the scan vacuous, and a vacuous scan reads green)."""
    for line in str(text).splitlines():
        if line.strip():
            return " ".join(line.split()).lower()
    return ""

# ── W4 (adv, D-8) · the two-strikes halt MIGRATES from `type: verdict` to `type: escalation` ─────
#
# The halt was a `verdict` whose body opened with ESCALATION_MARKER, because the vocabulary had no
# word for it (the "NO SIXTH MESSAGE TYPE" note at the finish edge states that constraint at
# length). W4 closes the vocabulary at SEVEN and `escalation` is one of them, so the record finally
# has its own type and the marker stops being the only thing that says what the row IS.
#
# ⚠ DUAL-READ, NOT A CUTOVER. Live buses hold rows written under the old encoding, and the
# at-most-once scan that keeps a milestone from escalating twice is exactly what re-fires if a
# pre-migration row goes unrecognised. Both types are therefore accepted by every reader, and the
# marker stays load-bearing on both. SUNSET: drop `"verdict"` from this tuple once no bus in service
# holds a pre-W4 escalation row — check with `fail-status --json` per live milestone before doing it.
ESCALATION_TYPES = ("escalation", "verdict")

# The `milestone-<id>` value the escalation family keys on used to ride in `why:` — a free-text
# field with 2 writers and 4 readers pattern-matching it (adv, C41). W4 gives it its own header
# key. Same dual-read posture, same reason, and both are WRITTEN during the sunset window so no
# pre-W4 reader (or pinned selftest row) changes its answer.
MILESTONE_WHY_PREFIX = "milestone-"

# W4 (adv, C42) — the chat-thread id's shape, kept identical to the ferry's own
# `bus-ferry.js#THREAD_ID_RE`. The ferry fails CLOSED on a malformed token (the row silently takes
# the ordinary DM path), so the shape is checked HERE, where the sender still holds the message.
CHAT_THREAD_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}:\d+\.\d+$")


def milestone_clause(milestone_id):
    """The legacy `why:` clause for a milestone — one composer, so the writers and the fallback
    reader below cannot drift about what the pre-W4 encoding looked like."""
    return f"{MILESTONE_WHY_PREFIX}{milestone_id}"


def milestone_of(b):
    """The milestone a message block belongs to, or None. Prefers the `milestone:` header key and
    falls back to the pre-W4 `why: milestone-<id>` encoding — ONE reader for both, so every scan in
    the escalation family answers identically on an old row and a new one."""
    if b.get("milestone"):
        return b["milestone"]
    why = b.get("why") or ""
    return why[len(MILESTONE_WHY_PREFIX):] if why.startswith(MILESTONE_WHY_PREFIX) else None

# ---- the retry threshold: ONE authority (IPH-11) -----------------------------------------------
#
# The bar `escalate` compares the derived count against. Absent everywhere it is 2 — the
# two-strikes number this verb shipped with. Two rungs override it, first hit wins:
#   1. the milestone's own `retry-threshold` cell in `<goal>/milestones.csv`  (per-milestone)
#   2. `<goal>/retry-threshold`, one integer                                  (per-goal default)
# `<goal>` is `base.parent`: `base_dir` builds base as `<goal>/coordination` (the same derivation
# `cmd_reap` states at length beside its own use). No new path plumbing.
#
# FAIL-CLOSED ON A BAD VALUE, and the direction is the whole point: this reader is the code that
# raises the owner's alarm. Refusing here would append NO escalation row, so one junk character
# would silently switch the safety OFF. A junk value warns on stderr and the next rung answers.
# Refusing loudly is the WRITER's job (`rbtv-goal retry-threshold --set`).
#
# The floor is 1, never 0: the gate reads `count < bar`, so `bar = 0` is never true and a goal
# would escalate on ZERO fails.
RETRY_THRESHOLD_DEFAULT = 2
RETRY_THRESHOLD_FILE = "retry-threshold"
RETRY_THRESHOLD_COLUMN = "retry-threshold"


def _retry_threshold_int(raw, where):
    """`raw` as a threshold >= 1, or None plus ONE stderr line saying which value was ignored.

    `.strip()` is load-bearing, not tidiness: the live goal-root markers on the Windows vault are
    CRLF-terminated and `int("3\\r\\n")` raises."""
    try:
        n = int(raw.strip())
    except ValueError:
        n = None
    if n is None or n < 1:
        print(f"warning: {where}: retry threshold {raw.strip()!r} is not an integer >= 1 — "
              f"ignoring it and falling back (the bar below 1 would escalate on zero FAILs)",
              file=sys.stderr)
        return None
    return n


def resolve_retry_threshold(base, milestone_id):
    """(bar, source) — the escalation bar for this milestone and WHICH rung answered
    (`milestone` | `goal` | `default`). The gate and every surface that REPORTS the bar call
    this one function, so the reported bar and the enforced bar are one object."""
    root = base.parent
    path = root / "milestones.csv"
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            # By column NAME: two milestones.csv header shapes are live in this workspace
            # (`milestone-id,name,status` and `milestone-id,title,done-when,state`), so a
            # positional read is wrong on one of them. An absent column falls through.
            for row in csv.DictReader(fh):
                if (row.get("milestone-id") or "").strip() != str(milestone_id):
                    continue
                cell = (row.get(RETRY_THRESHOLD_COLUMN) or "").strip()
                if cell:
                    n = _retry_threshold_int(cell, f"{path} ({milestone_id})")
                    if n is not None:
                        return n, "milestone"
                break
    except (OSError, csv.Error):
        pass
    try:
        raw = (root / RETRY_THRESHOLD_FILE).read_text(encoding="utf-8")
    except OSError:
        raw = ""
    if raw.strip():
        n = _retry_threshold_int(raw, str(root / RETRY_THRESHOLD_FILE))
        if n is not None:
            return n, "goal"
    return RETRY_THRESHOLD_DEFAULT, "default"


def escalation_row(base, milestone_id):
    """The milestone's escalation row, or None — the one scan `escalate` and `fail-status`
    share, so "already escalated" means the same thing to both."""
    want = str(milestone_id)
    return next((b for b in load_messages(base)[1]
                 if b["type"] in ESCALATION_TYPES and milestone_of(b) == want
                 and ESCALATION_MARKER in "\n".join(b["lines"][1:])), None)


def escalation_discharged(base, milestone_id):
    """True when the milestone's escalation row exists AND a later trial verdict for the same
    milestone reads PASS — the case `fail-status` must stop reporting as a permanent HALTED.
    False when there is no escalation, or the escalation is still the newest word on the
    milestone (a still-open escalation, or one followed only by more FAILs).

    Ordering is the log's own `num` — monotonic, allocated under `coord_lock` — never a
    timestamp: two rows can share a `now()` second but never a `num`."""
    esc = escalation_row(base, milestone_id)
    if esc is None:
        return False
    want = str(milestone_id)
    for b in load_messages(base)[1]:
        if b["num"] <= esc["num"] or b["type"] != "verdict" or milestone_of(b) != want:
            continue
        m = VERDICT_CLAUSE.search("\n".join(b["lines"][1:]))
        if m and m.group(1).upper() == "PASS":
            return True
    return False


def trailing_fail_verdicts(base, milestone_id):
    """The length of the TRAILING run of FAIL trial verdicts for `milestone_id` — the two-strikes
    count, recomputed from the log every call. Walks from the tail over `type: verdict` rows
    whose `why:` is `milestone-<id>`, counting while the body's verdict clause reads FAIL and
    stopping at the first PASS (or clause-less row). Escalation records are skipped: they are
    not trials. Returns 0 for a milestone with no verdict rows."""
    _, blocks = load_messages(base)
    want = str(milestone_id)
    count = 0
    for b in reversed(blocks):
        # `type: escalation` rows are skipped by this filter outright; the marker test below still
        # runs for the pre-W4 escalations that were written as verdicts (ESCALATION_TYPES' sunset).
        if b["type"] != "verdict" or milestone_of(b) != want:
            continue
        body = "\n".join(b["lines"][1:])
        if ESCALATION_MARKER in body:
            continue
        m = VERDICT_CLAUSE.search(body)
        if m and m.group(1).upper() == "FAIL":
            count += 1
            continue
        break
    return count


def escalate_if_second_fail(base, milestone_id, sender):
    """On the milestone's Nth consecutive FAIL — N being the resolved retry threshold — append
    EXACTLY ONE escalation row and return the derived count; return None otherwise (below the
    bar, or the row already exists). Derivation, existence scan and append share ONE
    `coord_lock` hold, so two concurrent judges cannot both observe "no escalation yet" (the
    same race append_message's own lock closes for numbering).

    ⚠ THE RECIPIENT IS THE RESERVED `owner` TOKEN AND IS NOT A PARAMETER
    (`decisions.md#d-agents-address-owner-not-master`, owner, 2026-08-09). One verb, one legal
    recipient: an initiation toward the human addresses `owner`, and a seat that never types an
    address cannot type the wrong one. This append is also the ONE write path that reaches
    `_append_message_unlocked` — which validates nothing — so the token is pinned here rather
    than trusted from a caller."""
    want = milestone_clause(milestone_id)
    with coord_lock(base):
        count = trailing_fail_verdicts(base, milestone_id)
        bar, _source = resolve_retry_threshold(base, milestone_id)
        if count < bar:
            return None
        _, blocks = load_messages(base)
        for b in blocks:
            if (b["type"] in ESCALATION_TYPES and milestone_of(b) == str(milestone_id)
                    and ESCALATION_MARKER in "\n".join(b["lines"][1:])):
                return None
        # W4 (adv, D-8): the halt is a `type: escalation` row now, carrying its milestone in the
        # `milestone:` key. `why:` is written too, for the sunset window — a pre-W4 reader (and
        # every selftest row pinning the old clause) still sees exactly what it saw.
        _append_message_unlocked(
            base, sender, OWNER_TOKEN, "escalation",
            f"{ESCALATION_MARKER}\n"
            f"{count} consecutive FAIL verdicts for {want} (bar: {bar}) — the gap-wave loop "
            f"halts here; this row travels the owner channel and waits for the owner's answer.",
            why=want, milestone=str(milestone_id))
        return count


def cmd_escalate(args):
    """The two-strikes escalation as a VERB (planning-v4 D12, finding F1): the dod-judge seat is
    an agent OCCUPANT, and an occupant cannot call a Python helper — only the CLI. THIN BY
    DESIGN: the derived-count and at-most-once invariants live in `escalate_if_second_fail`
    (one coord_lock hold over derive + scan + append) and are NOT restated here; this wrapper
    resolves base and identity, calls the helper, and names which of the three outcomes
    happened — the helper's None covers BOTH quiet outcomes, so the split is READ off the log
    (an existing escalation row is what "already" means), never re-derived."""
    base = base_dir(args)
    sender = resolve_agent(args)
    count = escalate_if_second_fail(base, args.milestone, sender)
    want = f"milestone-{args.milestone}"
    row = escalation_row(base, args.milestone)
    bar, source = resolve_retry_threshold(base, args.milestone)
    if count is not None:
        print(f"escalated: sent message #{row['num']} ({sender} -> {OWNER_TOKEN}, "
              f"type: {row['type']}, milestone: {args.milestone}) — {count} consecutive FAIL "
              f"verdicts (bar: {bar}, from {source})")
    elif row is not None:
        print(f"already-escalated: message #{row['num']} already carries {want}'s escalation "
              f"row — nothing appended (at-most-once)")
    else:
        # The bar is REPORTED from the same resolver the gate enforced, never re-stated as a
        # literal: this line printed `(bar: 2)` while the gate compared against something else
        # for exactly as long as the number was hardcoded in two places.
        print(f"below-bar: trailing FAIL count for {want} is "
              f"{trailing_fail_verdicts(base, args.milestone)} (bar: {bar}, from {source}) — "
              f"nothing appended")


# ── THE LOOP RE-FIRE (owner ruling 2026-08-12) — deterministic routing at the verdict edge ──────
#
# `concepts/workflow-edge.md`: "the loop re-fire — a loop's validation seat emits a fail verdict
# and the edge reading it re-launches the loop branch"; `concepts/loop.md`: the FAIL-verdict redo
# is "a fresh worker re-dispatched on the slot", bounded by the retry budget. Judgment produced
# the verdict; the ROUTING is this code — no pass-opener agent, no seat self-evaluation. The
# route is DECLARED on the judge's own seat descriptor (`on-fail-relaunch:` in seat.md
# frontmatter, materialized from the workflow's seats.csv), because the loop's shape differs per
# workflow and per judge; a judge declaring none gets exactly the old behavior.

ON_FAIL_RELAUNCH_KEY = "on-fail-relaunch"


def on_fail_relaunch_route(base, seat):
    """The caller seat's declared loop route — the `on-fail-relaunch:` frontmatter list in its
    own `{package}/seats/<seat>/seat.md` (block list or `[a, b]` flow). `[]` when the file, the
    frontmatter, or the key is absent: no declaration means no loop, never a guessed one."""
    raw = _ferry_read(Path(base).parent / "seats" / str(seat) / "seat.md")
    if raw is None:
        return []
    fm = _ferry_frontmatter(raw)
    m = re.search(rf"^{ON_FAIL_RELAUNCH_KEY}:[ \t]*(.*)$", fm, re.MULTILINE)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline.startswith("[") and inline.endswith("]"):
        return [t.strip().strip("'\"") for t in inline[1:-1].split(",") if t.strip()]
    out = []
    # `m.end()` sits before the key line's own newline — strip it, or the scan's first "line" is
    # the empty string and the block list reads as absent.
    for line in fm[m.end():].lstrip("\r\n").splitlines():
        lm = re.match(r"^[ \t]*-[ \t]*(\S+)", line)
        if not lm:
            break
        out.append(lm.group(1).strip().strip("'\""))
    return out


def cmd_verdict(args):
    """IPH-26 — the trial verdict as a VERB, and THE ONLY DOOR THAT CAN ARM THE ESCALATION GATE.

    Every escalation reader keys on the header clause `why: milestone-<id>` (`escalation_row`,
    `trailing_fail_verdicts`, `escalate_if_second_fail`, `escalate`, `fail-status`). Until this
    verb there was NO WRITER: `send --why` takes `choices=sorted(BROADCAST_CLAUSES)` — bare words
    only, no `milestone-<id>` — and refuses `--why` outright to any recipient but `all`. So the
    whole retry-threshold mechanism was inert from a seat, `fail-status` always answered 0, and
    the dod-judge prompt ordered a composition the CLI could not accept. `send --why` is NOT
    widened (owner ruling): one purpose-built verb instead.

    THE VERB COMPOSES THE FIRST BODY LINE (`verdict: PASS` / `verdict: FAIL`); the occupant
    supplies only the per-clause evidence. That is load-bearing, not tidiness.
    `trailing_fail_verdicts` walks from the NEWEST row backwards and STOPS at the first row whose
    body carries no verdict clause — so ONE malformed body appended last zeroes the count no
    matter how many FAILs precede it, and a judge that formats its own first line wrongly
    silently disarms its own halt. Mechanizing the line makes that unrepresentable.

    RECORDING A VERDICT AND CHECKING THE BAR ARE ONE ACT (owner ruling): this ends in
    `cmd_escalate`, unconditionally, including on `--pass`. No branch, no escape hatch — a PASS
    makes the trailing count 0, so the gate appends nothing and simply says so, and the
    pre-existing `escalate` verb is already the idempotent hatch for a re-check.

    ROUTING (owner ruling). A FAIL row and a PASS row BOTH go to the PASS-OPENER — the seat that
    queues the next wave from this verdict (`dod-judge.md` step 5: "on every arm, the pass-opener
    acts next on this verdict"). The judge writes nothing to its own folder. Only the ESCALATION
    row carries `owner`, and that recipient stays pinned inside `escalate_if_second_fail`. The
    split is what keeps the owner's chat quiet: `bridges/chat/bus-ferry.js` ferries `owner`-
    addressed rows into the owner's chat, so a routine verdict carrying `owner` would ping a human
    on every trial. The fixer hears every verdict; the owner is pinged once, at the bar.

    ⚠ `--to` IS AN ARGUMENT, NOT A TOKEN, and it is REQUIRED. The pass-opener's seat id differs
    per goal (`forg-judge`'s goal names its own; `plan-dod-judge` is materialized nowhere), so a
    literal would be wrong everywhere but one goal. It is not DERIVED either, and that was
    checked rather than assumed: the pass-opener is a LOOP BACK to the seat that opened the pass,
    and `taskforce.csv`'s `after` column is a DAG — it cannot carry a back-edge. Measured on the
    one live goal that rosters a judge (`forge-reference-seat-id-naming`), NOTHING declares
    `after: forg-judge`, so a derivation would answer "no successor" on the only case there is.
    The seat's prompt names where the value comes from; inventing a registry for it was refused.

    ⚠ LOCK SAFETY — SEQUENTIAL, NEVER NESTED. `append_message` takes AND RELEASES its own
    `coord_lock`; `escalate_if_second_fail` then takes a FRESH one. They are deliberately not
    wrapped in a single hold: a nested `coord_lock` on a second fd of the same .lock file
    deadlocks under flock (see `_append_message_unlocked`). The benign race that leaves is
    disclosed rather than hidden: a concurrent judge appending between the two calls changes only
    WHICH invocation reports the escalation. At-most-once still holds, because the existence scan
    lives inside the escalation's own hold.
    """
    base = base_dir(args)
    sender = resolve_agent(args)
    mid = str(args.milestone)
    # The `why:` field is parsed back as `[^|]*?` on ONE header line (MSG_HEADER), so a pipe
    # corrupts the field and a newline destroys the line; `to:` is parsed as `\S+`, so any
    # whitespace in the recipient does the same. Refused HERE because the log is append-only: a
    # corrupted header is permanent residue that no later read can repair.
    for label, value, ws_fatal in (("milestone id", mid, False),
                                   ("--to recipient", str(args.to), True)):
        if (not value.strip() or any(ch in value for ch in "|\r\n")
                or (ws_fatal and value.split() != [value])):
            refuse(
                "input",
                f"{label} {value!r} cannot go in a message header — it is blank, or it "
                f"carries a `|`, a newline, or (for a recipient) whitespace. The header is one "
                f"line with `|`-separated fields, so this row would be unparseable FOREVER in an "
                f"append-only log.\nPass the bare id (e.g. m3) and one seat name.",
                1)
    # MILESTONE REGISTRY CHECK, DELIBERATELY ADVISORY. Every live `milestones.csv` in this
    # workspace is header-only, so refusing an unknown id would refuse every verdict in
    # production — the gate would be a total outage dressed as rigour.
    # ponytail: warn-only when NOTHING could be checked. Upgrade path: refuse on an unknown id
    # once a goal actually seeds milestone rows — and add that refusal to `escalate` and
    # `fail-status` in the SAME change, or three verbs will disagree about what a milestone is.
    try:
        with open(base.parent / "milestones.csv", encoding="utf-8", newline="") as fh:
            seeded = [r for r in csv.DictReader(fh) if (r.get("milestone-id") or "").strip()]
    except (OSError, csv.Error):
        seeded = []
    if not seeded:
        print(f"warning: {base.parent / 'milestones.csv'} seeds no milestone rows, so "
              f"'{mid}' could not be checked against any registry — this verdict is being "
              f"recorded on an unverified id.", file=sys.stderr)
    want = milestone_clause(mid)
    # NEVER A SECOND WRITER OF THE LOG: `append_message`, the same door `send` uses, with its own
    # lock and its own numbering. Never `_append_message_unlocked`, never `messages.md` by hand.
    # W4 (adv, C41): the milestone rides its OWN key now; `why:` carries the legacy clause through
    # the sunset window so no pre-W4 reader and no pinned selftest row changes its answer.
    n = append_message(base, sender, args.to, "verdict",
                       f"verdict: {args.clause}\n{message_body(args)}", why=want, milestone=mid)
    print(f"verdict {args.clause}: sent message #{n} ({sender} -> {args.to}, type: verdict, "
          f"why: {want})")
    return cmd_escalate(args)


def cmd_fail_status(args):
    """READ-ONLY: what the escalation gate would decide for this milestone right now.

    The pass-opener used to RE-DERIVE the count and the bar itself — a second implementation of
    the authority, free to disagree with the one that enforces. This verb is the authority's own
    answer: `bar` comes from `resolve_retry_threshold` and `fail_count` from
    `trailing_fail_verdicts`, the two functions `escalate` itself calls."""
    base = base_dir(args, register=False)   # a command whose contract is "this writes nothing"
    count = trailing_fail_verdicts(base, args.milestone)
    bar, source = resolve_retry_threshold(base, args.milestone)
    at_bar = count >= bar
    escalated = escalation_row(base, args.milestone) is not None
    # `escalated` is kept as raw history — an at-most-once fact about the log, never erased by a
    # later PASS. `halted` is the derived, discharge-aware authority every consumer must gate on:
    # true while at the bar, or while an escalation stands with no newer PASS verdict for this
    # milestone; false once a PASS clears it, even though `escalated` still reads true.
    discharged = escalated and escalation_discharged(base, args.milestone)
    halted = at_bar or (escalated and not discharged)
    payload = {
        "milestone": args.milestone,
        "fail_count": count,
        "bar": bar,
        "at_bar": at_bar,
        "escalated": escalated,
        "discharged": discharged,
        "halted": halted,
        "source": source,
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"milestone-{payload['milestone']}: {payload['fail_count']} consecutive FAIL "
              f"verdict(s), bar {payload['bar']} (from {payload['source']})")
        print(f"at-bar: {str(payload['at_bar']).lower()}   "
              f"escalated: {str(payload['escalated']).lower()}   "
              f"halted: {str(payload['halted']).lower()}")
        if payload["halted"]:
            print("=> the contract is HALTED: queue nothing here until the owner answers")
        elif payload["escalated"]:
            print("=> escalation discharged: a later PASS cleared the halt, queueing may resume")
        else:
            print("=> below the bar: one gap-fill pass is warranted")
    return 0


# ── W7 · THE QUEUE-REQUEST READ PATH ───────────────────────────────────────────────────────────
#
# ⚠ COORD.PY STAYS THE ONE BUS PARSER (adv, C66/fidelity-2). The engine consumer gets NO JavaScript
# reader of `messages.md`: a second parser of an append-only log written by this file is the drift
# `MSG_HEADER` exists to prevent, and it would drift silently — a header key this file adds is a
# key that reader silently drops. The engine shells `queue-requests --json` exactly as it already
# shells `send`.
#
# THE IDEMPOTENCY KEY IS THE FIRST BODY LINE, and it is three fields, not one (adv, C66):
#
#     queue-request: <milestone-id>/<verdict-id>/<pass-kind>
#
# `pass_kind` JOINS the key because a gap-fill re-trigger is the DESIGNED second event on the same
# milestone — it must not hash as a duplicate of the initial pass, and it must not re-add the
# initial pass's seats. `<verdict-id>` is the message number of the verdict row this request was
# minted from, which is what makes the supersession lookup below a LOOKUP rather than a
# re-derivation from milestones.csv.
#
# ⚠ THE KEY IS A BODY LINE AND THE `milestone:` HEADER KEY IS NOT ITS SOURCE. `concepts/
# body-sigil.md` argues a machine-read mechanic belongs in a header key, and it is right; the
# divergence is deliberate and bounded: `milestone` IS read from the header (authoritative), and
# the body line carries only the two fields the wire form has no key for. It is transcribed to the
# KG at landing rather than left as an undeclared convention.
QUEUE_REQUEST_KEY = re.compile(r"^queue-request:\s*(?P<key>\S+)\s*$")


def queue_request_rows(base):
    """Every `queue-request` row of this goal's log, oldest first, with its key decomposed and
    both supersession facts resolved.

    Two DIFFERENT supersessions, and conflating them would drop live work:
      · `superseded`        — THIS request row was superseded by a later one.
      · `verdict_superseded` — the VERDICT the request was minted from was superseded (adv, C72;
        the #42 -> #46 supersession happened on the flagship). The consumer skips these. It is a
        LOOKUP of one message number, never a re-derivation from `milestones.csv` — "the engine
        TRUSTS the checker" is about not re-deriving readiness, not about ignoring a retraction.

    A row whose first body line is not the key parses with `key: null` and every derived field
    null. It is REPORTED, never dropped: a malformed request that vanishes from this listing is
    the D7 shape again (a correct derivation with no mechanical consequence), and the consumer
    can refuse it loudly instead of never seeing it."""
    _, blocks = load_messages(base)
    superseded = {b["supersedes"] for b in blocks if b["supersedes"] is not None}
    rows = []
    for b in blocks:
        if b["type"] != "queue-request":
            continue
        key = None
        for line in b["lines"][1:]:                # [0] is the header line itself
            if not line.strip():
                continue
            m = QUEUE_REQUEST_KEY.match(line.strip())
            key = m.group("key") if m else None
            break                                  # FIRST non-blank body line or nothing
        parts = key.split("/") if key else []
        vid = parts[1] if len(parts) == 3 and parts[1].isdigit() else None
        rows.append({
            "num": b["num"],
            "key": key if len(parts) == 3 else None,
            # The HEADER key is authoritative for the milestone; the body's first field is the
            # same value and is kept only so the key string round-trips.
            "milestone": b["milestone"],
            "verdict_id": int(vid) if vid else None,
            "pass_kind": parts[2] if len(parts) == 3 else None,
            "sender": b["sender"],
            "ts": b["ts"],
            "superseded": b["num"] in superseded,
            "verdict_superseded": bool(vid) and int(vid) in superseded,
            "body": "\n".join(b["lines"][1:]).strip(),
        })
    return rows


def cmd_queue_requests(args):
    """READ-ONLY: the goal's `queue-request` rows, for the engine's queue-request pass.

    Writes nothing — not even a run-tag registration — for the same reason `fail-status` does not:
    the daemon reads this on every cadence, and a read that mutates the roster would register the
    daemon as an occupant of every goal it looks at."""
    base = base_dir(args, register=False)
    rows = queue_request_rows(base)
    if not getattr(args, "all", False):
        rows = [r for r in rows if not r["superseded"] and not r["verdict_superseded"]]
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print("no queue-request rows")
        return 0
    for r in rows:
        flags = " ".join(f for f, on in (("SUPERSEDED", r["superseded"]),
                                         ("VERDICT-SUPERSEDED", r["verdict_superseded"]),
                                         ("MALFORMED-KEY", r["key"] is None)) if on)
        print(f"#{r['num']} {r['key'] or '(no key line)'} from {r['sender']} "
              f"{r['ts']}{'  ' + flags if flags else ''}")
    return 0


def log_delivery_failures(base, failures):
    """P22 — a lost wake must be visible in the LOG, not only on the sender's terminal."""
    if not failures:
        return
    with coord_lock(base):
        with open(base / "messages.md", "a", encoding="utf-8") as f:
            for fail in failures:
                f.write(f"> delivery-failure: {fail}\n")


def relay_seats(token, decls):
    """Every seat in THIS package declaring `relays: <token>` — the resolution of a role word.

    DERIVED from descriptors, never a kit-side name list, for the reason `inbox_decls` states at
    length: a name list in the kit freezes ONE campaign's role vocabulary into a tool every run
    shares. It also keeps the resolution HONEST — `probe_master_bound.py`'s M6 asserts the kit does
    not contain the live master seat's name, so a fix that hard-coded it would go green while
    rebuilding the exact defect stage 3 removed.

    PACKAGE-SCOPED BY CONSTRUCTION: `decls` is built from this package's own briefings, so a
    foreign seat sharing a roster name cannot be resolved here at all. That is not incidental —
    `G-111` is exactly this, live: a seat of a CLOSED run still running and sharing the live run's
    roster name, so an unscoped resolution would deliver this run's `send master` into a dead one.
    (The seat is deliberately not named here: `probe_master_bound.py`'s M6 asserts mechanically
    that the kit does not contain the live relay seat's name, and a comment naming it would defeat
    that check while proving nothing.)

    N SEATS IS A VALID ANSWER, not an ambiguity. The KG is explicit that the master is ONE ROLE
    over ONE shared state realized by N live sessions, safe because no master session owns private
    durable state, so two live master sessions cannot diverge into two masters. N deliveries are
    therefore N copies to ONE recipient. Refusing on N>1 would make the owner channel fail
    precisely when it is most redundant."""
    if not token:
        return frozenset()
    t = token.lower()
    return frozenset(s for s, d in (decls or {}).items() if t in (d.get("relays") or ()))


def sender_admitted(b, bound, decls):
    """Does a bounded inbox admit message `b`'s sender? The SENDER half of relay resolution.

    Two ways in, and the split is deliberate:

      LITERAL — the sender's own seat name is in the bound. Unchanged, and no origin test: this is
      exactly today's behaviour for every existing bound, and narrowing it while adding a feature
      would be a silent regression dressed as a fix.

      RELAY — the bound names a role TOKEN and the sender declares it. This one IS origin-tested:
      a message carrying `from-pkg:` was written from outside this package (stage 4), so its sender
      is not the seat this package's descriptors describe. Without that test a foreign seat named
      like the local relay-holder would inherit the local master's reach — asserted identity beating
      verified identity, which is `G-111` itself.

    A bound that is None means UNBOUNDED and never reaches here."""
    if b["sender"] in bound:
        return True
    if b.get("origin"):
        return False
    return any(b["sender"] in relay_seats(tok, decls) for tok in bound)


def addressed_to(b, agent, gmap, observers, mode="any", closing=(), decls=None):
    """Is message `b` in `agent`'s inbox? `mode` is the --addressed vocabulary: `any` = to me,
    my groups, or everyone (an observer seat sees the full log); `direct` = only messages naming
    me; `broadcast` = only messages to all.

    G-20/G-21 are applied HERE, in the one predicate `read`, `status` and every unread count share,
    so no view can disagree with another about what a seat's inbox holds — the same reason the
    unread derivation was collapsed into `unread_for`.

    `closing` is the set of seats currently being closed (`load_closing`); pass it or a closing
    seat is filtered by role only."""
    to = b["to"]
    is_closing = agent in closing
    # THE SENDER BOUND, applied before any addressing question: `r-cos-bounded-inbox` and
    # `r-engineer-contact` bound an inbox to NAMED SENDERS, and that is a property of WHO IS
    # SPEAKING, not of how the message is addressed — so it cuts a broadcast, a group message and a
    # by-name message alike. That is the owner's sentence in full ("receiving all messages, not only
    # those addressed to him; only u and master can talk to him"): one declared field answers both
    # halves.
    #
    # This is BELT-AND-BRACES, not the enforcement: `send` refuses a non-permitted sender at the
    # CLI (see cmd_send), so a bounded message should never reach the log at all. This catches the
    # two that can — a `--force` override, and a message that predates the bound. It is safe to cut
    # here for exactly the reason the closing cut is: the sender was told at send time and still
    # HOLDS its message, so nothing is accepted-then-dropped. And it is never SILENT — `read`'s
    # withheld footer names every message addressed to this seat that this predicate cut, with its
    # number, which is what keeps a bound from manufacturing G-94's failure while fixing its family.
    #
    # No descriptor in any package declares `senders:` today, so this is None for every seat and
    # the mechanism ships INERT until one does.
    bound = ((decls or {}).get(agent) or {}).get("senders")
    if bound is not None and not sender_admitted(b, bound, decls):
        return False
    # A RELAY TOKEN is a by-name address in effect, and is branched EXPLICITLY rather than reusing
    # the group machinery — which is the tempting reuse, since a group gives addressing, wake, read
    # and recipient validation for free. It would be wrong: `G-32` makes group fan-out honour the
    # same TYPE scope test as `all`, so `send master --type note` would be silently dropped for a
    # special-case seat. The master's traffic is a by-name address and must never be type-scoped.
    to_relay = to != "all" and to not in gmap and agent in relay_seats(to, decls)
    if to == "all":
        # A special-case seat, or any seat mid-close, is cut from the room's broadcast — by TYPE
        # for the watcher, entirely for the rest. Applied before the observer short-circuit: an
        # observer reads the full log by grant, but the owner's directive is about what LANDS in
        # a system seat's inbox, and a grant to read everything is not an obligation to receive it.
        if is_closing or not in_broadcast_scope(agent, b["type"], decls):
            return False
    elif to in gmap and agent in gmap.get(to, ()):
        # G-32: a GROUP is not a side door around the broadcast cut. The traffic the owner cut at
        # the front door walked in this one — the watcher sat in three of the run's four groups, so
        # essentially the whole room's lane traffic still landed in the seat the directive was
        # written to protect. Group fan-out therefore honours the SAME scope test as `all`: the
        # watcher keeps completion/verdict (its DAG trigger), closers and `engineer` keep nothing,
        # and a seat mid-close is cut entirely. Membership refusal (create-group/add-to-group) is
        # the braces; this is the belt, so even a deliberately-added member is filtered by TYPE
        # rather than by anyone remembering the rule. A message addressed to the seat BY NAME is
        # untouched — that invariant is what makes every one of these cuts safe.
        if is_closing or not in_broadcast_scope(agent, b["type"], decls):
            return False
    elif is_closing and (to == agent or to_relay) and not closing_reaches(agent, b["sender"], None):
        # Belt-and-braces: `send` refuses a peer's direct message to a closing seat at the CLI, so
        # one should never reach the log. If one does (a --force override, or a message that
        # predates the state), it still must not spend the seat's remaining context.
        return False
    if mode == "direct":
        # `--addressed direct` means "only messages naming me". A relay token names the seat
        # carrying it just as surely as its seat name does — that is what resolution MEANS — so
        # excluding it here would hide the owner channel's own traffic from the filter a seat uses
        # to find what was addressed to it.
        return to == agent or to_relay
    if mode == "broadcast":
        return to == "all"
    if agent in observers:
        return True
    return to == agent or to_relay or to == "all" or (to in gmap and agent in gmap[to])


def sender_origin(args, sender):
    """Where `sender` is writing FROM, or None when it is a member of the package it writes INTO.

    G-94's root, in one sentence: a sender may write into a package it is not rostered in, the log
    records only its role name, and every downstream visibility and reachability decision is then
    made against a roster that does not describe that sender at all. `resolve_agent` permits the
    claim precisely because the calling pane has no roster row IN THE TARGET PACKAGE — which is
    exactly the cross-package case — so the permission is right and the RECORD was incomplete.

    THE TEST IS THE CALLING PANE, NOT THE NAME, and that distinction is the entire fix. Asking
    "does a seat of this name belong to this package" is CIRCULAR — run-2 has a `leader` seat, so
    run-1's leader writing into run-2 answers YES and goes unlabelled, which is precisely the
    handover G-94 lost. Measured, not reasoned: that membership-by-name version returned None for
    the exact case it existed to catch. The pane is the ONE identity claim the tool can verify
    (`pane_agent`'s own docstring), so it is what verified-vs-asserted must be decided on.

    An unresolvable pane returns None — today's behaviour exactly. Under-labelling is the safe
    direction: it preserves the status quo for out-of-pane callers like watch.py, whereas
    over-labelling would stop a seat's own sends being suppressed and re-serve them to it.

    NOT a refusal. Cross-package sending is legitimate and this run does it deliberately — a
    leader hands a run off, a liaison answers on another package's log. What was missing was the
    record of it, so the label is additive and never blocks."""
    try:
        pane = detect_pane(getattr(args, "pane", None))
        if not pane:
            return None        # cannot verify anything; change nothing
        if pane_agent(base_dir(args), pane):
            # This pane holds an active row in THIS package — either as `sender`, or as the row
            # resolve_agent already vetted a --force claim against. Local.
            return None
    except Exception:
        return None            # never let bookkeeping about a send break the send
    # No ACTIVE roster row for this pane. That is NOT the same as foreign, and treating it as such
    # was this function's defect: a seat that has checked out — or was renewed, or never checked in
    # — keeps writing from inside its own package, and every one of its messages was stamped
    # `external`. Measured: all four origin-labelled messages in run-2's log were the owner-liaison,
    # local and rostered, sending while its row read inactive. Under the stage-5 sender bound a
    # relay token is refused for any message carrying an origin, so that mislabel would have
    # SEVERED THE OWNER CHANNEL the moment `relays: master` was declared.
    #
    # So resolve the caller's OWN package from its cwd and compare: the NEAREST enclosing package
    # is where the caller is writing from. Same package -> local, whatever the roster says. A
    # different one -> name it, which is exactly G-111 (a closed run's seat still resolves to its
    # own package and stays refused). Only a cwd inside no package at all is `external`, which now
    # means what it says: no package this tool could identify.
    #
    # The earlier form walked PAST this package looking for any other, so it could also attribute a
    # caller to an ANCESTOR package it merely sat under. Stopping at the nearest fixes both.
    try:
        here = Path.cwd().resolve()
        pkg = package_dir(args)
        for cand in (here, *here.parents):
            if (cand / "coordination").is_dir():
                return None if cand == pkg else cand.name
    except Exception:
        pass
    return "external"


def is_own_send(b, agent):
    """Is `b` a message THIS seat sent? (G-94 — the cut that ate a lifecycle handover.)

    The old test was `b["sender"] == agent`: a NAME comparison. A name is a ROLE, and roles repeat
    across packages, so when run-1's leader wrote `from: leader | to: leader` into run-2's package
    the receiving leader classified it as its own send, `read` answered "no new messages", and the
    cursor advanced past it — the message was addressed to it, was never shown, and was never
    re-offered. Correct in its designed case (a seat must not be re-served its own traffic) and
    wrong for two distinct seats wearing one name.

    A message carrying an ORIGIN was written from OUTSIDE this package, so whoever sent it is by
    construction not the local seat reading it, whatever the two are called. Absence of an origin
    means local, which is every message written before the field existed — so this is exactly the
    old behaviour for every historical log, and the fix is FORWARD-LOOKING by necessity: the
    record for the handover that motivated it does not carry the distinguisher, and inventing one
    retroactively would be rewriting the permanent log. That message stays disclosed by `read`'s
    withheld footer instead, which is what stage 1 exists for."""
    return b["sender"] == agent and not b.get("origin")


def shows_in_inbox(b, agent, gmap, observers, mode="any", closing=(), decls=None):
    """THE one answer to "will `agent`'s `read` show message `b`" — `read`, `unread_for` and the
    WAKE half all route through it.

    `addressed_to` already collapsed the READ-side views into one predicate so no two of them could
    disagree about a seat's inbox. The wake half was never brought in: `deliver_wakes` re-derived a
    weaker test of its own (`in_broadcast_scope` on the `all` and group branches, `closing_reaches`
    on the direct branch, and NO visibility test at all on a bare direct message), so the wake set
    and the read set drifted apart in both directions. A seat with `auto-wake: yes` was woken for
    every direct message in the room and could read none of them — the pure-overhead version of the
    very interruption a bounded inbox exists to prevent — while the code's own comment already
    stated the invariant it was breaking.

    The `sender != agent` half lives here rather than in `addressed_to` because it is a property of
    the READER, not of the addressing: `addressed_to` answers "is this in my inbox", and a seat's
    own sends are in its inbox and simply must not be re-served to it.
    """
    return not is_own_send(b, agent) and addressed_to(b, agent, gmap, observers, mode, closing,
                                                      decls)


def why_not_woken(b, agent, gmap, observers, decls=None):
    """The REASON `agent` is not woken, for the sender's summary line (T3: a narrowed inbox is
    never silent at either end — the sender always learns who did not get the nudge, and why)."""
    bound = ((decls or {}).get(agent) or {}).get("senders")
    if bound is not None and not sender_admitted(b, bound, decls):
        # Named distinctly from the generic cut: this one is about WHO IS SPEAKING, and a sender
        # told only "not in its inbox" would look for the fault in its addressing.
        return "bounded inbox: you are not a permitted sender"
    if b["to"] == "all" or (b["to"] in gmap and agent in gmap.get(b["to"], ())):
        if not in_broadcast_scope(agent, b["type"], decls):
            return "special-case seat"
    return "not in its inbox"


def open_escalations(blocks):
    """Escalation rows nobody has answered — W4 (adv, C47), for `pending`'s nag view.

    ⚠ VISIBILITY, NOT A HOLD. An escalation is not an `ask` and never becomes one: `open_asks`
    filters on `type == "ask"`, so an escalation opens NO check-out hold for its sender (adv, C45 —
    the leader must not be HELD by its own escalation, and it is not, by construction rather than
    by an exclusion list). This function only makes an unanswered halt impossible to scroll past.
    Nothing here starts a timeout; `d-auto-proceed-declined` is untouched.

    An escalation LEAVES THIS VIEW two ways and two only: a row carrying `re: <its number>` — which
    NAMES the row it closes — and a supersession, for the same reason an ask does.

    ⚠ THE THIRD ARM IS DELETED [D-4-ruling, C-3, T1-R12, C8]. W8 (adv, C78) used to retire the
    escalating seat's OLDEST still-open halt on ANY unnumbered `answer` from the owner. That is the
    guess the redesign exists to end: an owner reply about one halt silently retired a different
    one, and the rule was HEAD-only, so nobody watching Slack could see which row it had taken.
    Owner-facing release now binds to the Slack THREAD the ask was posted in plus an authorized
    sender, and it lives where that thread does — `bridges/chat/ask-thread.js`, backed by the
    daemon's `open_asks` row (`spec-owner-io` §2.4, `spec-state-store` §3). Nothing on this bus
    releases anything any more.

    ⚠ WHAT SURVIVES HERE IS A RENDER, NOT A DOOR. `re:` is a LOG FIELD: it says which numbered row
    an answer was written about, and this view honours it so a numbered reply stops nagging. It
    opens no hold, reaps no wait, fires no relaunch and flips no stored state — `open_asks` filters
    `type == "ask"` and an escalation is never one (C45). An unnumbered owner answer now settles
    NOTHING here, which is the correct reading of a reply that named no row.

    ⚠ TWO ARMS, and the marker is required on ONLY ONE of them. `type: escalation` is sufficient by
    itself (a leader's escalation composes its own body and carries no marker); the marker test
    applies to the pre-W4 encoding alone, where it is the ONLY thing distinguishing a halt from an
    ordinary trial verdict. Requiring it on both would hide every leader escalation — which is the
    row this view exists for."""
    superseded = {b["supersedes"] for b in blocks if b["supersedes"] is not None}
    answered = _settled_nums(blocks)
    rows = [b for b in blocks
            if (b["type"] == "escalation"
                or (b["type"] == "verdict" and ESCALATION_MARKER in "\n".join(b["lines"][1:])))
            and b["num"] not in superseded and b["num"] not in answered]
    return rows


def _reply_settles(reply, target):
    """Does `reply` (an answer/verdict carrying `re: <target's num>`) actually settle `target`?

    G-92/G-134: the old test was "any block anywhere carries `re: <n>`" with NO CHECK on who sent
    it, so a reply meant for one row — or a peer instead of the addressed party — silently retired
    an unrelated halt. Measured live: stools escalations #237, #248 and #270, each addressed to
    `owner`, were all closed by `goal-master`, a PEER worker, never by the owner. A reply only
    settles the row it names when it comes from the party the row was ADDRESSED TO (the ordinary
    ask/answer shape: the owner answering its own escalation, a seat answering a question aimed at
    it) or from the row's OWN sender (the escalator/asker recording on the bus that it is settled
    — W8 arm 5, `leader` transcribing "the owner ruled" onto its own escalation) — never a third
    seat wearing neither hat."""
    return reply["sender"] in (target["to"], target["sender"])


def _settled_nums(blocks):
    """Numbers of `ask`/`escalation` rows genuinely settled by a `re:` reply — ONE predicate,
    shared by `open_escalations` and `open_asks` (G-134 criterion 2: reuse it, don't grow a
    second opinion). `--re` is write-gated to `--type answer`/`verdict` (`cmd_send`), so the type
    filter here only documents that invariant rather than widening it."""
    by_num = {b["num"]: b for b in blocks}
    settled = set()
    for b in blocks:
        if b["re"] is None or b["type"] not in ("answer", "verdict"):
            continue
        target = by_num.get(b["re"])
        if target is None or _reply_settles(b, target):
            settled.add(b["re"])
    return settled


def open_asks(blocks, sender=None, to=None, base=None):
    """Asks nobody has settled: type ask, not superseded, and no answer/verdict carrying `re:`
    its number (T4/F11 — before the link existed, an unanswered ask was invisible without
    re-reading the whole log).

    `sender` and `to` NARROW this one answer; they never compute a second one. `pending` passes
    neither and gets the room's open asks. The check-out hold (D8) passes both and gets "does THIS
    seat have an unanswered ask TO THE OWNER" — so the view a seat reads before it leaves and the
    gate that stops it leaving cannot disagree about what is open. `sender` goes through
    `is_own_send`, never a name compare, for G-94's reason: a foreign seat wearing this seat's role
    name must not hold it here any more than it may fill its inbox there.

    `base`, when given, drops an ask whose SENDER seat has since finished or exited (G-92/G-134
    criterion 3): nothing here ever expired on the asking seat's own lifecycle, so an ask nagged
    `pending` forever after the seat that raised it was gone — #165/#473 stayed open long after
    their seats did. "Finished" reads the roster's own `active` column (the same column `status`
    and `workers` already read), never a second liveness test. A sender with NO roster row at all
    is kept — absence of a row means a foreign, cross-package sender (ADDRESSABLE NON-MEMBERS,
    top of file), not a seat that finished; only a row that says `active: no` is evidence of
    that."""
    superseded = {b["supersedes"] for b in blocks if b["supersedes"] is not None}
    settled = _settled_nums(blocks)
    rows = [b for b in blocks
            if b["type"] == "ask" and b["num"] not in superseded and b["num"] not in settled
            and (sender is None or is_own_send(b, sender))
            and (to is None or b["to"] == to)]
    if base is not None:
        _, _, roster = load_workers(base)
        rows = [b for b in rows
                if (row := current_row(roster, b["sender"])) is None or row["active"] == "yes"]
    return rows


def age_of(ts):
    """Age of a message timestamp in m/h ('?' when unparseable)."""
    try:
        dt = datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return "?"
    mins = max(0, int((datetime.now() - dt).total_seconds() // 60))
    return f"{mins}m" if mins < 90 else f"{mins // 60}h"


def split_log_notes(b):
    """(body lines, log-annotation lines) for one message block.

    P22 appends its `> delivery-failure:` lines to messages.md AFTER the block they follow, so
    `load_messages` absorbs them into that block and a plain render showed them as if the sender
    had written them. They are the LOG speaking about a failed wake, never message content. The
    file itself is untouched (its grammar is frozen and the lines must stay findable there) —
    this is a RENDER split only: the reader gets them as a labelled trailer, never hidden."""
    body = [ln for ln in b["lines"][1:] if not ln.startswith("> delivery-failure:")]
    notes = [ln[2:] for ln in b["lines"][1:] if ln.startswith("> delivery-failure:")]
    return body, notes


def body_of(b):
    """A message's body WITHOUT the P22 delivery-failure annotations (one-line views only)."""
    return "\n".join(split_log_notes(b)[0]).strip()


SHELL_COMMS = {"bash", "sh", "dash", "zsh", "ksh", "fish", "csh", "tcsh"}

# Set true by main() only. See main() for why the distinction cannot be inferred.
CLI_INVOCATION = False


def parent_is_shell():
    """Is this process's parent a shell — i.e. was our argv PARSED by one on the way in?"""
    try:
        return Path(f"/proc/{os.getppid()}/comm").read_text(encoding="utf-8").strip() \
            in SHELL_COMMS
    except OSError:
        return False


def shell_source_line():
    """The command string the PARENT was given, when the parent is a one-shot `sh -c <string>`.

    This is the ONE place the PRE-SUBSTITUTION text still exists. By the time coord.py receives
    argv the shell has already run every `backtick` and $(...) and replaced it with the output —
    undetectable from the body alone, which is why S-4(b) bit three authors who KNEW about it.
    '' when the parent is an interactive shell (no -c) or unreadable: that case is genuinely
    undetectable and the gate below stays silent rather than guessing."""
    try:
        raw = Path(f"/proc/{os.getppid()}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return ""
    parts = [p.decode("utf-8", "replace") for p in raw if p]
    if len(parts) >= 3 and Path(parts[0]).name in SHELL_COMMS and parts[1].startswith("-") \
            and "c" in parts[1]:
        return parts[2]
    return ""


def substitution_eaten(body):
    """The substitution markers the invoking shell consumed before coord.py saw this body.

    A marker present in the shell's ORIGINAL command string and absent from what arrived was
    substituted away — the body in hand is not the body the author wrote. Once, this executed
    the launch command a renewal broadcast was merely describing: a second live leader for four
    minutes, and the record of how to recover a dead leader no longer contained the recovery.

    THE BOUND, stated rather than implied: this catches a body sent through `sh -c`, which is
    every agent-harness and every scripted send. It CANNOT catch a human typing at an
    interactive prompt — there is no -c string to compare against — and it does not need to
    catch a programmatic caller passing an argv LIST, which was never exposed."""
    line = shell_source_line()
    if not line:
        return []
    return [m for m in ("`", "$(") if m in line and m not in body]


def message_body(args):
    """The body: the positional, or --file PATH / --file - (stdin). A file/stdin body never
    passes through a shell — the fix for the backtick-substitution class that corrupted msg #77
    (F6)."""
    src = getattr(args, "file", None)
    msg = getattr(args, "message", None)
    if src and msg:
        refuse(
            "input",
            "a quoted body AND --file were both given, and only one of them can be "
            "the message — silently picking one would send a body you did not read.\n"
            "Pass the message positionally OR via --file, not both.",
            1)
    if src:
        if src == "-":
            body = sys.stdin.read()
        else:
            p = Path(src)
            if not p.is_file():
                refuse(
                    "input",
                    f"--file {src} — no such file, so there is no body to send.\n"
                    f"Write the file first, or pass an absolute path (relative paths resolve "
                    f"from YOUR working directory, not the package's).",
                    1)
            body = p.read_text(encoding="utf-8")
    elif msg:
        body = msg
    else:
        refuse(
            "input",
            'no message body — pass "<msg>", or --file PATH (--file - reads stdin) '
            'when the body carries backticks, quotes, or newlines',
            1)
    body = body.strip("\n")
    if not body.strip():
        refuse(
            "input",
            "the body is empty (whitespace only) — an empty message costs every "
            "recipient a wake and a read, and says nothing.\nWrite the content, or drop the "
            "send.",
            1)
    return body


def known_recipients(args, base):
    """Every name `send` can deliver to: roster rows ∪ briefing `agent:` names (a seat that
    exists but has not launched yet) ∪ group names ∪ RELAY TOKENS that resolve ∪ 'all'.

    A relay token resolves from EITHER side of the room (7.546): a local seat declaring `relays:`
    (`inbox_decls`, below) or an addressable non-member declaring it in its own descriptor
    (`load_addressable`, folded into the one grant at the end of this function). The second source
    is what gives a FRESH run a legal `master` address at all — its nine planning seats declare no
    role, so before it the rulebook told a stuck seat to say so on a bus that would refuse it.

    A relay token is admitted ONLY while some seat declares it. That asymmetry is deliberate: an
    unresolved `master` stays an unknown recipient and is refused with the near-match hint, which
    is the right answer — accepting an address nobody holds is how `S-7` opens a thread with no
    possible terminus. This is also the SEND-side half of `#184`'s both-directions ruling: before
    it, `master` was not a valid recipient at all, so a bounded seat could receive from the master
    and could never answer it."""
    _, _, rows = load_workers(base)
    names = {r["agent"] for r in rows}
    names |= set(briefing_frontmatters(workers_dir(args)))
    names |= launch.registered_seats(package_dir(args))
    names |= set(group_map(base))
    for d in inbox_decls(args).values():
        names |= set(d.get("relays") or ())
    names.add("all")
    # `owner` IS ALWAYS A LEGAL ADDRESS (d-agents-address-owner-not-master). It is not a seat and
    # never resolves to one: it is the reserved token the chat bridge's ferry routes to the human,
    # under gates that are the BRIDGE's to apply. It is admitted unconditionally — an agent must
    # never be told "unknown recipient" for the one address the ruling tells it to initiate to.
    names.add(OWNER_TOKEN)
    # `auto` IS ALWAYS A LEGAL ADDRESS TOO (D2), for the same reason and with a shorter life: it is
    # the routed types' reserved token, RESOLVED at the top of `cmd_send` into a real recipient
    # before any gate sees it, so no row is ever addressed to it. Admitted here so a `--type note`
    # sent to `auto` meets D2's own teaching refusal rather than "unknown recipient — did you mean
    # …", and so the token appears in the `known:` list every refusal prints.
    names.add(AUTO_TOKEN)
    # THE ONE GRANT. An addressable non-member joins the recipient set and NOTHING else: it gains
    # no row above, so it is absent from the census, the sweep, every lifecycle command, the pane
    # cap, `to: all` fan-out and the wake pass — each of those reads the roster, not this set.
    # Because BOTH `cmd_send` gates consult this one predicate, admitting the name here fixes the
    # recipient half and the ask-refusal in a single move, which is what the ruling requires.
    names |= set(addressable_nonmembers(args, base)[0])
    return names


def cmd_send(args):
    base = base_dir(args)
    sender = resolve_agent(args)
    force = getattr(args, "force", False)
    body = message_body(args)
    _, blocks = load_messages(base)

    # ── D2 (owner ruling, 2026-08-19) · THE SENDER DOES NOT CHOOSE — `auto` and the routed types ─
    #
    # ⚠ IT RESOLVES FIRST, BEFORE EVERY GATE BELOW, and that ordering is the design rather than a
    # detail: `args.to` is rewritten to a REAL recipient here, so every existing gate — the
    # unknown-recipient refusal, the departed warning, the owner-ask gate, the master rule — sees
    # the resolved name and judges it on its own merits, and the resolved name is what the row
    # records. A human-interactive seat's `auto` ask therefore resolves to `owner` and then passes
    # the owner gate because it deserves to; an ordinary seat's resolves to a chair and never
    # reaches that gate at all. Nothing below had to learn about `auto`.
    #
    # The table itself is `routed_recipient`, and it is the ONE place it exists in code.
    _routed_to, _routed_why = ((None, None) if args.type not in ROUTED_TYPES
                               else attest.routed_recipient(args, base, args.type, sender))
    if args.to == AUTO_TOKEN:
        if args.type not in ROUTED_TYPES:
            refuse(
                "input",
                f"`{AUTO_TOKEN}` is not a recipient — it is the token that says THE SYSTEM PICKS "
                f"the recipient, and it is defined only for the ROUTED types "
                f"({', '.join(f'`{x}`' for x in ROUTED_TYPES)}). `--type {args.type}` is not one "
                f"of those: address the seat that must ACT, by name.\n"
                f"  {coord_invocation(args)} send <seat> \"<your message>\" --type note --inline\n"
                f"  — with `{args.type}` where that line says `note`.",
                1)
        args.to = _routed_to
        print(c(f"routed: `{AUTO_TOKEN}` -> `{args.to}` — {_routed_why}", C_HINT))
    # ⚠ `stuck` IS AUTO-ONLY. A brand-new type with zero legacy senders, so there is nothing to
    # break by closing it, and closing it is the whole ruling: an agent that picks a recipient for
    # a blocked signal is an agent deciding who to contact. No `--force`, same idiom and same
    # reason as the two closed gates further down — the escape hatch is the routed send.
    if args.type == "stuck" and args.to != _routed_to:
        refuse(
            "state",
            f"a `--type stuck` message does not choose its recipient — THE SYSTEM ROUTES IT, and "
            f"on this goal that is `{_routed_to}` ({_routed_why}). You addressed `{args.to}`.\n"
            f"Send it routed instead:\n"
            f"  {coord_invocation(args)} send {AUTO_TOKEN} \"<what you are blocked on>\" "
            f"--type stuck --inline\n"
            f"That is the whole rule for this type: say you are STUCK and say what on. Who reads "
            f"it, and who it escalates to if they cannot solve it, is not yours to work out.\n"
            f"There is no --force for this one: the ruling exists to delete exactly the judgment "
            f"an override would reintroduce.",
            1)

    # ── d-53 (owner ruling `d-53-redirect-to-leader`, 2026-08-31) · MAIL TO A SUMMONED-BUT-ASLEEP
    # CHAIR REDIRECTS TO LEADER, not option (a) refuse-loudly and not option (c) accept-and-pile-up.
    #
    # `goal-master` — the one name in `SUMMONED_SEATS` — does not wake on mail BY DESIGN (D24):
    # only the owner's own summon (a goal-channel message or `@rbtv` tag) starts it. Mail addressed
    # to it while it holds no live pane therefore had NO DRAIN PATH at all — it piled up unread
    # indefinitely, and that pile once ate the owner's OWN Slack asks (bus #33266/#33306,
    # 2026-08-20). Redirected HERE, before the unknown-recipient and departed checks below, so
    # every later gate — including those — sees the resolved `leader` and judges it on its own
    # merits, the same ordering discipline `auto` uses above.
    #
    # ⚠ ONLY WHILE ASLEEP. A `goal-master` currently summoned (an active roster row with a live
    # pane) is reached directly — redirecting a chair that IS awake would defeat the very summon
    # that woke it.
    #
    # Accepted consequence, stated by the owner: `leader` now receives some mail that is not
    # strictly its business — that is not a defect to design around.
    if is_summoned_seat(args.to):
        _sm_row = current_row(load_workers(base)[2], args.to)
        _sm_awake = bool(_sm_row) and _sm_row.get("active") == "yes" and is_tmux_pane(_sm_row.get("pane"))
        if not _sm_awake:
            print(c(f"redirected: `{args.to}` is a SUMMONED chair asleep by design — mail is not "
                    f"its wake term (D24), so it never drains what piles up there. Routed to "
                    f"`leader` instead.", C_HINT))
            args.to = "leader"

    # F5 — a typo'd recipient was accepted silently: the message landed under a name nobody
    # reads and the only signal was one "wake skipped" line the sender scrolled past.
    # Constraint 3: a register row that did not resolve is announced HERE, on the path that was
    # about to rely on it — not deferred to an audit nobody runs. A name silently missing from the
    # recipient set reads exactly like a name that was never admitted.
    report_addressable_errors(args, base)
    nonmembers = addressable_nonmembers(args, base)[0]
    # W3 (adv, C33) — the recipient set `send` gates on, WRAPPED HERE and never inside
    # `known_recipients`: that function's return set is selftest-keyed and is also what
    # `lifecycle_alarm_recipient` reads to resolve the `leader` chair for executor-failure alarms.
    known, departed = attest.send_recipients(args, base)
    # ⚠ `--force`-PROOF, and that is a CHANGE (adv, C33, specified rather than assumed). An unknown
    # recipient is not a rule that is wrong in some case: the message lands under a name nobody
    # reads, in an append-only log, and the only signal was one "wake skipped" line. The override
    # existed because the recipient set used to be narrower than the set of legitimate addresses —
    # staff chairs, in particular, were not in it. They are now, so the override has nothing left
    # to be right about.
    if args.to not in known:
        near = difflib.get_close_matches(args.to, sorted(known), n=1, cutoff=0.6)
        refuse(
            "state",
            f"'{args.to}' is not a known recipient — no roster row, no briefing, no "
            f"group, no relay token, no staff chair and no addressable non-member of that name."
            + (f" Did you mean '{near[0]}'?" if near else "")
            + f"\nknown: {', '.join(sorted(known))}\n"
            + "There is no --force for this one: a message addressed to a name nobody holds is "
              "permanent residue in an append-only log, and you still HOLD it at this refusal.",
            1)
    # …and a DEPARTED worker seat is accepted, LOUDLY. Not refused — its successor may read the log,
    # and the leader routes what it cannot — but never silent: this is the exact shape of a signal
    # delivered to an empty chair, and the sender is the one party who can still do something else.
    # Printed BEFORE the append and regardless of `--force`, for the same reason the refusal above
    # is force-proof: an override waives a gate, and a warning is not a gate.
    if args.to in departed:
        print(c(f"⚠ '{args.to}' has DEPARTED — its roster row is no longer active, so nothing will "
                f"be woken by this message and it may never be read. It IS in the log, addressed "
                f"to that name, and a successor sitting in that seat would see it.\n"
                f"  If this needs acting on, send it to `leader` instead — that chair is always "
                f"occupied on demand and it routes what it cannot settle.", C_DEAD),
              file=sys.stderr)
    # S-7 — an `ask` stays OPEN until an answer is addressed to its SENDER via --re, and
    # `known_recipients` refuses any name none of its five sources carries (roster, briefing,
    # group, relay token, addressable non-member). So an
    # ask from an unaddressable sender opens a thread WITH NO POSSIBLE TERMINUS: nobody can
    # close it, even in principle. A daemon-fired job sending under its own name — deliberately,
    # so flags are attributed to the detector that raised them rather than a borrowed seat —
    # accumulated 13 of these in one run, every one reported DELIVERED by the sending side and
    # every one permanent residue in an append-only log. The correct sibling shows the pairing
    # is load-bearing: watch.py also sends `ask` and is RIGHT to, because it sends AS `watcher`,
    # a real answerable seat. The TYPE was copied without the IDENTITY.
    #
    # One check, at the only moment it is cheap. NO --force override, deliberately and unlike
    # every other gate in this function: those refuse things that are wrong in the usual case
    # but right in some case. There is no state of the world in which opening an unclosable ask
    # is correct — the sender wants `flag` or `note`, both of which need no reply.
    if args.type == "ask" and sender not in known:
        refuse(
            "state",
            f"'{sender}' cannot receive a reply — no roster row, no briefing and no "
            f"group of that name — so an `ask` from you would stay OPEN forever. An answer "
            f"must be addressed to its sender (--re), and nobody can address you.\n"
            f"Send this as --type note (FYI) or --type flag if the type exists, or check in "
            f"first so you have a roster row: {coord_invocation(args)} checkin {sender} "
            f"\"<what you are doing>\".\n"
            # G-165: for a NON-MEMBER that check-in line is the FORBIDDEN repair, and this text
            # recommending it is how the trap reaches every next meta-agent. The correspondent
            # that hit it declined the advice and said so; the next one will not have that
            # context, so the alternative is named here rather than left to a ruling it cannot
            # read.
            f"⚠ If you are NOT a member of this run (a meta-agent with its own goal folder), do "
            f"NOT check in — that would make you a member, which is the thing you are not. Ask "
            f"this package to admit you as an addressable non-member instead: add your "
            f"descriptor's path to {package_dir(args)}/addressable.csv and declare "
            f"`addressable: non-member` in that descriptor. You then resolve as a recipient and "
            f"gain nothing else — in particular NO WAKE: delivery is PULL, and you must read the "
            f"log yourself.\n"
            f"There is no --force for this one: 13 asks opened this way in one run and not "
            f"one of them can ever be closed.",
            1)

    # ── W4 (adv, C43 / D-2c) · THE ESCALATION IDENTITY GATE ─────────────────────────────────────
    #
    # ⚠ IT LIVES HERE, AT `cmd_send`, AND NOT AT THE WRITER — the one deliberate exception to the
    # choke-point rule, for the same reason the `known_recipients` wrapper is one. `resolve_agent`
    # runs HERE; `_append_message_unlocked` has no identity and never will. Threading a
    # self-asserted sender string down to the writer and checking it there would be a gate that
    # tests the claim against itself — guaranteed green, and worse than no gate because it reads
    # like one.
    #
    # WHO MAY ESCALATE: the LEADER, or a JUDGE. Both arms are mechanical:
    #   · `leader` — the staff chair W3 minted. Escalating what it could not fix IS its commission.
    #   · a judge — a seat whose own `seat.md` declares `on-fail-relaunch:`, which is the ONLY
    #     mechanical judge signal this file has (`on_fail_relaunch_route`, the loop re-fire's
    #     source of truth). A judge's ORDINARY route to this type is not this verb at all: the
    #     two-strikes halt is written from inside `escalate_if_second_fail`, under the `escalate` /
    #     `verdict` verbs, which never pass through here. This arm exists so a judge that must
    #     escalate something the bar did not catch is not forced to lie about its type.
    # Everyone else routes through the leader — which is the entire point of staffing that chair.
    if args.type == "escalation" and sender != "leader" and not on_fail_relaunch_route(base, sender):
        refuse(
            "state",
            f"'{sender}' may not send `--type escalation`. An escalation is the record of a halt "
            f"nobody inside the run can clear — it travels the owner channel and interrupts a "
            f"human, so the authority to raise one is held by the `leader` chair and by a judge "
            f"(a seat declaring `{ON_FAIL_RELAUNCH_KEY}:` in its seat.md).\n"
            f"What to do instead: send this to `leader` as an --type ask. That chair is always "
            f"occupied on demand, it can widen your cage or relaunch you, and it escalates what it "
            f"genuinely cannot fix — which is one more filter than you crossing this door.\n"
            f"If you ARE the milestone judge, the verb is `{coord_invocation(args)} verdict` / "
            f"`escalate`: the two-strikes halt is composed for you, at the resolved bar.\n"
            f"There is no --force for this one: an escalation nobody authorized still wakes the "
            f"owner, and the log is append-only.",
            1)

    # ── W8 (adv, C77) · THE ESCALATION IS ITS OWN DURABLE RECORD, AND ITS FIRST LINE IS THE KEY ─
    #
    # The ruling asked for ONE durable record written at escalation time that is (a) the dedup key
    # a re-woken leader reads instead of minting a second halt about the same blocker, and (b) the
    # "escalated, awaiting owner" state an operator view can read. Both already exist and neither
    # needed a new file or a new header field: the append-only log IS the record, `open_escalations`
    # IS the at-most-once scan, and `pending` already renders it under "UNANSWERED ESCALATIONS".
    #
    # WHAT WAS MISSING IS A KEY. The judge family has one — `ESCALATION_MARKER` as the row's FIRST
    # BODY LINE, which is how `escalation_row` finds a halt that landed on an earlier invocation.
    # A leader's escalation composes its own body and had none, so nothing could tell two rows
    # about one blocker from two rows about two. This reuses that existing pattern rather than
    # inventing a second one: THE FIRST LINE IS THE KEY, normalized. `--why` is deliberately NOT
    # used — on `send` it is `choices=BROADCAST_CLAUSES`, a closed four-word vocabulary the help
    # text explicitly refuses to widen, and widening it here would put a free-text key in a field
    # four other readers treat as an enum.
    #
    # ⚠ AT-MOST-ONCE, NOT ONCE-EVER. It refuses only while that escalation is still OPEN; once the
    # row is settled — by an answer carrying `re: <its number>`, or by a supersession; the
    # unnumbered-owner-answer arm is DELETED, see `open_escalations` — the same key may be raised
    # again, because a blocker that returns after a ruling is new information. And no
    # --force: the escape hatch is a first line that says a different thing, which is the honest
    # act — if it IS a different blocker, it does not read the same.
    if args.type == "escalation":
        _esc_key = _escalation_key(body)
        if not _esc_key:
            refuse(
                "input",
                "an escalation's FIRST LINE is its key in this log — a short, stable naming of "
                "the BLOCKER (e.g. `escalation: alpha's cage refuses the data root`). This body "
                "opens with no such line. Write one, then the halt below it.\n"
                "It is not a title: it is what stops a re-woken sitting raising the same blocker "
                "a second time while the owner is still reading the first, and what an operator "
                f"sees in {coord_invocation(args)} pending.",
                1)
        _dup = [b for b in open_escalations(load_messages(base)[1])
                if _escalation_key(body_of(b)) == _esc_key]
        if _dup:
            refuse(
                "state",
                f"ALREADY ESCALATED — message #{_dup[0]['num']} opens with this same first line "
                f"and the owner has not answered it, so the run is already halted on exactly this "
                f"blocker. A second row interrupts him twice for one decision and gives the log "
                f"two records of one halt.\n"
                f"  #{_dup[0]['num']} ({_dup[0]['sender']}): {truncate(body_of(_dup[0]), 160)}\n"
                f"NEW EVIDENCE for the same blocker goes on the log as a `note`. A DIFFERENT "
                f"blocker gets its own first line. There is no --force: the escape hatch is an "
                f"honest key, not an override.",
                1)

    # ── W8 (owner ruling D-7) · AN OWNER-ASK FROM A NON-INTERACTIVE SEAT FAILS LOUDLY, AT SEND ───
    #
    # D3's shape: a seat asks the owner, the ferry's gates park the row (nobody is watching this
    # goal, or this seat is not the one that may talk to a human), and NOTHING retries or escalates
    # it. The seat believes it asked. The ruling replaces that silence with a refusal at the door —
    # the sender still HOLDS the message, and it is told where the question can actually be
    # answered: the staff chairs, which are occupied on demand and which no gate parks.
    #
    # ⚠ THE PARK IS NOT DELETED, IT IS DEMOTED TO A BACKSTOP. The ferry keeps its gates for every
    # row this door never sees (a row written by a non-seat writer, a legacy row, an interactive
    # seat's ask when the GOAL is autonomous). Parked-ask semantics for `human-interactive` seats
    # are untouched — this refuses the class that could never be answered, and no other.
    #
    # ⚠ SCOPED TO SEATS THAT HAVE A DESCRIPTOR, deliberately. `seat_is_human_interactive` reads
    # `seats/<name>/seat.md` BY PATH (the ferry's own read), and it answers False for every name
    # with no descriptor at all — the master, the console, a daemon-fired job, an addressable
    # non-member. Gating on the bare False would refuse all of them, which is a rule about seats
    # applied to everything that is not one. The descriptor's EXISTENCE is the membership test.
    #
    # ⚠ NO `--force`, BY OWNER RULING (2026-08-15, closeout R5.7) — and it is a DELIBERATE REVERSAL
    # of how W8 first shipped this gate. W8 admitted `force` here because the D8 hold fixture drove
    # `cmd_send` with `force=True` on exactly this shape and the seat-behalf transports all carry
    # `force`. Both reasons were wrong on inspection: the D8 fixture's forced ask is now authored
    # while its descriptor still permits it (see the `bqp` note in the D8 hold rows), and NO
    # transport anywhere sends `--type ask` to the owner — they send `note`, `answer`,
    # `queue-request` and `verdict` (swept across the tree, 2026-08-15). More to the point, `force`
    # could not be right here: this gate refuses the class of ask that CAN NEVER BE ANSWERED, so an
    # override buys a row nobody will ever read. It now matches its two sibling gates below, which
    # carry no override for the same reason.
    if args.type == "ask" and args.to == OWNER_TOKEN:
        _pkg_hi = package_dir(args)
        _has_seat_md = (_ferry_safe_name(sender)
                        and _ferry_read(Path(_pkg_hi) / "seats" / str(sender) / "seat.md") is not None)
        if _has_seat_md and not seat_is_human_interactive(_pkg_hi, sender):
            _staff = [s for s in STAFF_SEATS
                      if (Path(_pkg_hi) / "seats" / s / "seat.md").exists() or s == "leader"]
            refuse(
                "state",
                f"'{sender}' is NOT flagged `human-interactive:` in its seat.md, so a question "
                f"addressed to the owner cannot reach him: the chat ferry PARKS it at the gate — "
                f"nothing posted, nothing retried, no answer possible, ever. You would be holding "
                f"a hold nobody can clear.\n"
                f"ASK THE STAFF INSTEAD — those chairs are occupied on demand, no gate parks their "
                f"mail, and the leader escalates to the owner what genuinely needs him:\n"
                f"  {coord_invocation(args)} send {_staff[0]} \"<your question>\" --type ask "
                f"--inline\n"
                + (f"  (a `{_staff[1]}` is staffed on this goal too — send guidance-shaped "
                   f"questions there and authority-shaped ones to `leader`)\n"
                   if len(_staff) > 1 else "")
                + f"If you genuinely may talk to the human, that is a DESCRIPTOR fact, not a send "
                  f"flag: `human-interactive: yes` in your seat.md, set by whoever authored the "
                  f"seat. THERE IS NO `--force` FOR THIS ONE: the refusal is not about permission, "
                  f"it is about reachability — a forced row is still a row nobody will ever read.",
                1)

    # ⚠ AGENTS NEVER INITIATE TO `master` (`decisions.md#d-agents-address-owner-not-master`,
    # owner, 2026-08-09). A `to: master` row is legal ONLY as an ANSWER to something master sent —
    # on this bus, a row carrying `--re <n>`. An initiation goes to `owner` instead, and everything
    # else goes to the seat BY NAME. Enforced HERE, at the CLI, for the same reason every other
    # bound in this function is: the log is append-only, so a mis-addressed row is permanent
    # residue, and the sender still HOLDS the message at a refusal.
    #
    # NO --force, deliberately: this is not a rule that is wrong in some case. The ruling's whole
    # value is that it is trivially teachable and closed — three lines with no judgment call — and
    # an override would reintroduce exactly the judgment that drifted.
    #
    # The MASTER itself is exempt (it initiates to whom it likes), and so is any answer.
    if (args.to == MASTER_TOKEN and sender != MASTER_TOKEN
            and getattr(args, "re_num", None) is None):
        refuse(
            "input",
            f"an agent NEVER INITIATES to `{MASTER_TOKEN}` — `decisions.md#"
            f"d-agents-address-owner-not-master` (owner, 2026-08-09). The rule is three lines:\n"
            f"  initiate -> `{OWNER_TOKEN}`   the reserved token the chat bridge ferries to the "
            f"human (gated there, parked when the gates say no)\n"
            f"  answer   -> the asker  a `to: {MASTER_TOKEN}` row is legal only with --re <n> "
            f"answering what master sent you\n"
            f"  else     -> the NAME   address the seat directly ('channel-master' by name is "
            f"always legal; it is the ROLE TOKEN that is restricted)\n"
            f"So: send this to `{OWNER_TOKEN}` if you are raising it with the human, or add "
            f"--re <n> if it answers a message master sent you.\n"
            f"There is no --force for this one: the ruling is closed, and an override is the "
            f"judgment call it exists to delete.",
            1)

    # G-22 / #198 — the two enforcement halves of the broadcast discipline. `all` costs every seat
    # a wake and a read, so it must be justified rather than habitual: a broadcast names the clause
    # it claims, and `note` — the type that was 35 of a live run's 86 broadcasts — cannot claim any,
    # because a note is by definition something a seat that never reads it still acts correctly
    # without. The cheap channel is a GROUP; before this, none had ever been created.
    why = getattr(args, "why", None)
    if args.to == "all" and not force:
        if args.type == "note":
            refuse(
                "input",
                f"a `note` is never an `all` broadcast — if a seat that never reads it "
                f"still acts correctly, it does not belong in everyone's inbox.\n"
                f"Send it to a GROUP (`{coord_invocation(args)} create-group <name> <members>`) "
                f"or direct to the seats who need it.\n"
                f"If it genuinely binds every seat, it is a verdict/completion under one of: "
                f"{', '.join(sorted(BROADCAST_CLAUSES))} — send it as that type with --why.\n"
                f"override: --force",
                1)
        if not why:
            clauses = "\n  ".join(f"{k} — {v}" for k, v in sorted(BROADCAST_CLAUSES.items()))
            refuse(
                "input",
                f"`send all` requires --why <clause>, naming what makes this everyone's "
                f"business:\n  {clauses}\n"
                f"If none of them fits, the message is not a broadcast — send it to a group or "
                f"direct.\noverride: --force",
                1)
    if why and args.to != "all":
        refuse(
            "input",
            f"--why justifies a BROADCAST and '{args.to}' is not `all`, so it would "
            f"record a clause for a message nobody needed one for.\nDrop --why.",
            1)

    # G-21 — a seat mid-close has one job left, so a peer's direct message is REFUSED here, at the
    # CLI, rather than accepted into a log the seat will depart without reading. The refusal is the
    # POINT: it fails loud, the sender still HOLDS its message and knows now, and nothing can be
    # orphaned. Queueing for a successor was the alternative and was ruled against (leader #189) —
    # it assumes a successor exists, and tonight five of six closes had none, so a queue whose
    # consumer may never exist is accept-then-silence with extra steps.
    entry = closing_entry(base, args.to)
    if entry is not None and not closing_reaches(args.to, sender, entry) and not force:
        closer = entry.get("closer") or f"closer-{args.to}"
        refuse(
            "state",
            f"'{args.to}' is CLOSING (since {entry.get('since', '?')}) — its inbox is "
            f"{closer} and leader only, so this message would arrive as work it will never do "
            f"and context its memory hand-off needs.\n"
            f"You still hold it, and nothing is lost: send it to leader, or wait for the seat's "
            f"successor if it is renewed and send it then.\n"
            f"override (you are certain the seat must read this before it goes): --force",
            1)

    # THE SENDER BOUND (`r-cos-bounded-inbox`, `r-engineer-contact`) — refused HERE, at the CLI,
    # because a bound enforced only at read time is the exact failure this family is being fixed
    # for: the message would be accepted, written to the permanent log, and then silently swallowed,
    # which is how G-94 lost a lifecycle handover. Refusing at send inverts that — the sender still
    # HOLDS its message, learns immediately, and is told the route that works.
    #
    # Only a BY-NAME message is refused. A broadcast or a group message is not: it legitimately
    # reaches every other member, and the bounded seat's copy is cut by `addressed_to` and then
    # NAMED in that seat's withheld footer. Refusing the whole broadcast because one member bounds
    # this sender out would narrow the room to protect one inbox.
    #
    # `origin` is resolved HERE rather than at append time because the bound test needs it: a relay
    # token is only honoured for a LOCAL sender (see `sender_admitted`), so the CLI refusal and the
    # read-time cut must be computed from the same inputs or they can disagree — which is this
    # seat's whole commission.
    origin = sender_origin(args, sender)
    decls = inbox_decls(args)
    probe = {"sender": sender, "origin": origin}
    # A relay token addresses N seats, so the bound question is asked of each: refuse only when the
    # message can reach NOBODY. A partial cut is not a refusal — the permitted seats still get it,
    # and each cut seat is named in the wake summary and in its own withheld footer.
    targets = sorted(relay_seats(args.to, decls)) or ([args.to] if args.to != "all" else [])
    bounds = {t: ((decls.get(t) or {}).get("senders")) for t in targets}
    reachable = [t for t, bd in bounds.items() if bd is None or sender_admitted(probe, bd, decls)]
    bound = bounds.get(args.to) if len(targets) == 1 and targets[0] == args.to else None
    if targets and not reachable and not force:
        if bound is None:                      # a relay token: name what it resolved to
            named = ", ".join(sorted(bounds))
            refuse(
                "state",
                f"'{args.to}' resolves to {named}, and every one of them has a BOUNDED "
                f"INBOX that '{sender}' is not among. This is a standing ruling about who may "
                f"spend those seats' context, not a judgement of your message.\n"
                f"You still hold it, and nothing is lost: send it to leader, who routes it.\n"
                f"override (it will still be filtered at each seat's read, though never silently "
                f"— their footers name it): --force",
                1)
        refuse(
            "state",
            f"'{args.to}' has a BOUNDED INBOX — it receives messages from "
            f"{', '.join(sorted(bound))} only, and '{sender}' is not among them. This is a "
            f"standing ruling about who may spend that seat's context, not a judgement of your "
            f"message.\n"
            f"You still hold it, and nothing is lost: send it to leader, who routes it.\n"
            f"override (and it will still be filtered at that seat's read, though never "
            f"silently — its footer names it): --force",
            1)
    # ⚠ THE ONE EXEMPTION: AN APPROVAL ROW IS A DOCUMENT BY CONSTRUCTION (G-plan-verifier-0827-2258).
    # The cap's reason is stated in its own refusal — "a body this long is a document, and every
    # agent pays for it at every checkpoint" — and an `--approve-commit` row is the one send where
    # every clause of that reason is false. It is addressed to `owner` and nothing else; no agent
    # inbox carries it; the bridge does not relay it as a note but opens an APPROVAL THREAD FROM IT
    # (`bus-ferry.js` → `chat-bridge.js#postOwnerAsk`, `kind: 'approval'`), where a one-word
    # `approve` starts execution — so the body IS the thing the owner reads before an irreversible
    # act, and "write it to a file and send the path" would hand the owner a path they cannot open.
    # Measured 2026-08-27 on `scratch-tool-inventory-8`: the digest fields `verify-plan.md` REQUIRES
    # measure 2300–2600 chars written tersely, so the contract and the cap could not both be met and
    # the seat sent with `--force` — an override that also waives every other gate on this path.
    # EXEMPTED rather than RAISED: a raised cap is a number that must be kept in step with a
    # required-field list living in another file, and it would lift the cap for every long note as
    # well. This lifts it for exactly the row whose reason does not apply.
    if len(body) > MESSAGE_MAX and not force and not (getattr(args, "approve_commit", None) or "").strip():
        # G-280 / task 7.94 criterion 3: this is the SECOND silent-failure path onto the same
        # surface argparse's echo bug hid behind — a seat that corrects its flags still loses a
        # long message here unless the failure is equally explicit. NOT SENT in those words,
        # matching the success path's "sent message #N": absence of that line is what a prose
        # reader does not notice. The cap itself (MESSAGE_MAX, communication.md's ratified rule)
        # is UNCHANGED — this only makes its refusal legible.
        refuse(
            "input",
            f"message NOT SENT — {len(body)} chars, max {MESSAGE_MAX}.\n"
            f"A body this long is a document, and every agent pays for it at every checkpoint. "
            f"Write it to a file, then send the PATH plus a 3-line summary: what it says, what "
            f"you want done with it, and by whom.\noverride: --force",
            1)
    if args.supersedes is not None and not any(b["num"] == args.supersedes for b in blocks):
        refuse(
            "state",
            f"--supersedes {args.supersedes} — no such message in the log (it ends at "
            f"#{blocks[-1]['num'] if blocks else 0}). A retraction pointing at nothing retracts "
            f"nothing.\nFind the number you meant: {coord_invocation(args)} read --digest --all",
            1)

    re_num = getattr(args, "re_num", None)
    if args.type == "answer" and re_num is None and not force:
        refuse(
            "input",
            "an answer must name the ask it answers — pass --re <ask#> (list them "
            "with `pending`).\nAn unlinked answer leaves the ask OPEN for every reader.\n"
            "override: --force",
            1)
    if re_num is not None and args.type not in ("answer", "verdict"):
        refuse(
            "input",
            f"--re is valid only on --type answer (required) and --type verdict "
            f"(optional) — not on '{args.type}'. A `re:` on any other type would make the "
            f"open-ask derivation lie.\nDrop --re, or send this as an answer.",
            1)
    if re_num is not None:
        target = next((b for b in blocks if b["num"] == re_num), None)
        if target is None:
            refuse(
                "state",
                f"--re {re_num} — no such message in the log (it ends at "
                f"#{blocks[-1]['num'] if blocks else 0}), so the ask would stay OPEN for every "
                f"reader.\nList the open asks: {coord_invocation(args)} pending",
                1)
        # W4 (adv, C47): an ESCALATION is settleable too, and the widening is load-bearing rather
        # than tidy. `pending` now shows unanswered escalations as things awaiting an answer; if
        # `--re` refused to point at one, the owner's answer could never be linked and the row
        # would nag FOREVER — a view that names a thing it makes unclosable is the silent-stall
        # shape this whole program is about.
        if target["type"] not in ("ask", "escalation"):
            refuse(
                "state",
                f"--re {re_num} — message #{re_num} is a '{target['type']}', not an "
                f"ask or an escalation; --re links an answer/verdict to the row it settles.\n"
                f"List what is open: {coord_invocation(args)} pending",
                1)

    # W4 (adv, C42) — the two chat-routing sigils as HEADER MECHANICS. `--deliver` says what the
    # named thread does with the row and means nothing without one, exactly as the body token did
    # (`bus-ferry.js#rowDeliver`), so it is refused alone rather than written to be ignored.
    chat_thread = getattr(args, "chat_thread", None)
    deliver = getattr(args, "deliver", None)
    if chat_thread and not CHAT_THREAD_ID_RE.match(chat_thread):
        refuse(
            "input",
            f"--chat-thread {chat_thread!r} is not a thread id — the shape is "
            f"`<CHANNEL>:<ts>` (e.g. C09ABCDEF:1754500000.123456), which is the plain "
            f"`chat-thread:` line at the top of your prompt.\n"
            f"The ferry fails CLOSED on a malformed token, so this row would have gone to the "
            f"owner's DM with no sign anything was wrong.",
            1)
    if deliver and not chat_thread:
        refuse(
            "input",
            f"--deliver {deliver} names what happens AT a thread and names no thread. Pass "
            f"--chat-thread <id> with it, or drop it.",
            1)
    # ⚠ `--milestone` IS BOUNDED TO `queue-request` (W7). W4 promoted `milestone:` to a header key
    # so the mechanic stops being pattern-matched out of free text, but `verdict` rows get theirs
    # from `cmd_verdict` — the ONE door that can arm the escalation gate — and widening this verb
    # to stamp a milestone on any type would give a second writer of the field every escalation
    # reader keys on. The queue-request needs it and has no other door, so it gets exactly that.
    if getattr(args, "milestone", None) and args.type != "queue-request":
        refuse(
            "input",
            f"--milestone is for `--type queue-request` only, and this row is a "
            f"`{args.type}`.\n"
            f"A `verdict` row's milestone is stamped by the verb that records it "
            f"(`coordinate verdict <milestone> --pass|--fail`), which is the one door that can "
            f"arm the escalation gate; a second writer of that field is a second authority over "
            f"the halt.",
            1)
    # ── THE APPROVAL AUTHORITY GATE (`--approve-commit`) ────────────────────────────────────────
    #
    # An `approve-commit:` on a `to: owner` row is what makes the bridge open a REAL APPROVAL
    # THREAD (`bus-ferry.js` -> `chat-bridge.js#postOwnerAsk` with `kind: 'approval'`), and in that
    # thread a one-word `approve` from the owner STARTS EXECUTION — the fourteenth gateway intent,
    # `start-execution.js`, materializing the plan the package binds. That door is IRREVERSIBLE and
    # it is opened by a row an agent writes, so the authority to write one is checked HERE, at
    # `cmd_send`, for the reason the escalation identity gate above lives here and not at the
    # writer: `resolve_agent` runs here and `_append_message_unlocked` has no identity. A check
    # further down would be testing a self-asserted sender against itself.
    #
    # THREE CONDITIONS, all mechanical, and no `--force` — an override on this one buys an
    # execution nobody authorized:
    #   1. the seat is DESIGNATED to reach the human (`human-interactive:` in its own seat.md) —
    #      the same descriptor fact the owner-ask gate above and the ferry's ask door both read;
    #   2. the goal HAS an approve-package — `start-execution.js` reads it and refuses
    #      `no-approve-package` loudly in the thread, so a row without one asks the owner to
    #      approve something the daemon will then decline to start;
    #   3. the commit on the row IS the package's `bound_commit` — an approval binds at a commit
    #      [T5-R5], and two different shas would mean the owner approved one tree and the daemon
    #      materialized another.
    approve_commit = (getattr(args, "approve_commit", None) or "").strip() or None
    if approve_commit:
        _pkg_ap = package_dir(args)
        if args.type != "note" or args.to != OWNER_TOKEN:
            refuse(
                "input",
                f"--approve-commit opens the owner's APPROVAL thread, and that is a `--type note` "
                f"addressed to `{OWNER_TOKEN}` — you sent a `{args.type}` to `{args.to}`.\n"
                f"  {coord_invocation(args)} send {OWNER_TOKEN} --file <your digest> --type note "
                f"--approve-commit <sha>\n"
                f"Drop the flag to send this row as what it is.",
                1)
        if not seat_is_human_interactive(_pkg_ap, sender):
            refuse(
                "state",
                f"'{sender}' may not open an APPROVAL thread. A reply of `approve` in that thread "
                f"STARTS EXECUTION of the plan — it is the one bus row that reaches through the "
                f"owner and back into the daemon — so it is written only by a seat DESIGNATED to "
                f"talk to the human: `human-interactive: yes` in {_pkg_ap}/seats/{sender}/seat.md, "
                f"set by whoever authored the seat. Yours does not say it.\n"
                f"Send the digest to `leader` as an --type ask instead; that chair routes what "
                f"genuinely needs the owner.\n"
                f"There is no --force for this one: the door it opens is irreversible.",
                1)
        _apkg = Path(_pkg_ap) / "planning" / "approve-package.json"
        try:
            _apkg_data = json.loads(_apkg.read_text(encoding="utf-8"))
        except FileNotFoundError:
            refuse(
                "state",
                f"there is no approve-package on this goal ({_apkg}), so an `approve` in the "
                f"thread you are about to open would be answered `no-approve-package` — the owner "
                f"would have approved a plan the daemon then refuses to start.\n"
                f"Write it FIRST, through its own writer, and pass the same commit:\n"
                f"  approve-package --goal-dir {_pkg_ap} --execution-goal <name> "
                f"--bound-commit <sha> --lane <lane> --plan-artifacts <path>\n"
                f"There is no --force for this one: the missing file is the answer, not the gate.",
                1)
        except (OSError, ValueError) as _apkg_err:
            refuse(
                "state",
                f"the approve-package at {_apkg} could not be read as JSON ({_apkg_err}), so the "
                f"commit on this row cannot be checked against it and the daemon will refuse the "
                f"approval anyway. Re-write it through the `approve-package` writer — never by "
                f"hand.",
                1)
        _bound = str((_apkg_data or {}).get("bound_commit") or "")
        if _bound != approve_commit:
            refuse(
                "state",
                f"--approve-commit {approve_commit} does not match the approve-package's "
                f"`bound_commit` ({_bound or 'absent'}) at {_apkg}. An approval BINDS AT A COMMIT "
                f"[T5-R5]: the owner would be reading a digest about one tree while the daemon "
                f"materializes another.\n"
                f"Send the package's own commit, or re-write the package for the tree you "
                f"actually checked.\n"
                f"There is no --force for this one: the two shas disagreeing IS the defect.",
                1)

    n = append_message(base, sender, args.to, args.type, body,
                       supersedes=args.supersedes, re_num=re_num, why=why, origin=origin,
                       milestone=getattr(args, "milestone", None),
                       chat_thread=chat_thread, deliver=deliver,
                       approve_commit=approve_commit)
    marks = ((f", supersedes #{args.supersedes}" if args.supersedes is not None else "")
             + (f", re #{re_num}" if re_num is not None else "")
             + (f", chat-thread: {chat_thread}" if chat_thread else "")
             + (f", deliver: {deliver}" if deliver else "")
             + (f", approve-commit: {approve_commit}" if approve_commit else "")
             + (f", why: {why}" if why else ""))
    # A cross-package send is called out to the SENDER too: the seat that most needs to know its
    # message landed on a roster that does not describe it is the one that just sent it.
    org_note = f" [from-pkg: {origin}]" if origin else ""
    # Leader's condition on `deliver to all`: PRINT THE RESOLVED SET. A bare "delivered to master"
    # is an unverifiable claim, and a role word that silently resolves to a different seat than the
    # sender assumed is `G-111` with better manners. Only for a token that actually resolved —
    # an ordinary recipient already names itself.
    resolved = sorted(relay_seats(args.to, decls))
    rel_note = f" [{args.to} -> {', '.join(resolved)}]" if resolved else ""
    print(f"sent message #{n} ({sender} -> {args.to}, type: {args.type}{marks}){org_note}{rel_note}")
    # B14 · THE LEDGER HALF OF THE SAME ACT. `--record` makes "recorded in the goal's decision
    # ledger" and "sent on the bus" ONE command, because a leader that has to remember two things
    # records one of them — the defect M15 names in its own words: *"a ruling recorded only in a
    # message is not recorded"*. It runs HERE, after the append, so the entry can CITE #N (the
    # ledger's consumption is anchor-resolution) and so the write with real failure modes goes
    # first. A failed ledger write is LOUD and exits non-zero with the exact text to add by hand —
    # the same discipline `session_close`'s refusal states: no swallow.
    _record_title = (getattr(args, "record", "") or "").strip()
    if _record_title:
        try:
            _led = record_decision(args, _record_title, body, caller=sender,
                                   to=args.to, mtype=args.type, num=n)
            print(f"recorded in the decision-log: {_led} (## {now()} — {_record_title})")
        except Exception as _led_err:                       # noqa: BLE001 — reported, never swallowed
            print(c(f"MESSAGE #{n} WAS SENT. THE LEDGER ENTRY WAS NOT WRITTEN: {_led_err}\n"
                    f"  The ruling is now recorded ONLY in a message, which is the exact state "
                    f"--record exists to prevent. Append this to the goal's decisions.md by hand:\n"
                    f"{decision_entry(_record_title, body, caller=sender, to=args.to, mtype=args.type, num=n)}",
                    C_DEAD), file=sys.stderr)
            sys.exit(1)
    # ⚠ SAID AT THE MOMENT IT MATTERS, to the person who most needs it: the sender who has just
    # addressed a non-member and would otherwise wait for a reply that no wake will ever prompt.
    # The ruling is explicit that leaving this implicit is the defect — silence would be read as
    # "considering" rather than "never delivered".
    # ⚠ `and not resolved` (7.546). Since a correspondent's declared ROLE TOKEN became an address,
    # a token can be BOTH admitted by the register and held by a live seat of this run — and then
    # the wake really does fire (`deliver_wakes` takes its `relayed` branch and nudges that seat).
    # Printing "no pane, never woken" beside a delivered wake would tell the sender the opposite
    # of what just happened. The hint belongs to the case it was written for: the address resolved
    # to NOBODY in this room.
    if args.to in nonmembers and not resolved:
        print(c(f"-- delivery is PULL, not push: '{args.to}' is an addressable NON-MEMBER — it has "
                f"no pane in this run and is NEVER woken. The message is in the log addressed to "
                f"it, and it must read the log itself. Silence from it means NOT YET READ, never "
                f"'considering'. If it is time-critical, confirm out of band.", C_HINT))
    # task 7.93 — the gateway send leg. INERT unless COORD_GATEWAY_TRANSPORT=1 (criterion 4); the
    # local append above and the wakes below are byte-identically what they were. Placed AFTER the
    # append deliberately: the local log is the room's substrate and must never be blocked on a
    # daemon being reachable.
    _g793_fail = gateway_send_leg(args, base, args.to, args.type, body)
    deliver_wakes(args, base, sender, args.to, n, args.type, origin)
    # d-111 — DEPARTED-SEAT AUTO-COPY. The warning above only ever told the SENDER to resend to
    # `leader` by hand; nothing acted on that advice, so a deliverable addressed to an empty chair
    # could sit unread indefinitely. This copies the same body to `leader` in the same send, as a
    # `note` (the original `--type` may be sender-restricted — e.g. `ask`/`escalation` — and a
    # copy is not the sender re-asking). `leader` can never itself be in `departed`
    # (`send_recipients` subtracts `STAFF_SEATS`), so this never re-copies a message already
    # addressed to leader.
    if args.to in departed:
        fwd_body = (f"[auto-copied — #{n} was addressed to `{args.to}`, a DEPARTED seat, and "
                    f"would otherwise sit unread]\n\n{body}")
        fwd_n = append_message(base, sender, "leader", "note", fwd_body, origin=origin)
        deliver_wakes(args, base, sender, "leader", fwd_n, "note", origin)
        print(f"  auto-copied to leader as #{fwd_n} (departed-seat routing)")
    if _g793_fail:
        # Loud, and non-zero. The message IS locally logged, so this is not a `refuse` — but a
        # contracted leg failed, and 7.94's whole finding is that a failed call must never read
        # as a successful one.
        print(c(f"  {_g793_fail}", C_DEAD))
        sys.exit(1)
    if args.type == "ask":
        print(c(f"next: {coord_invocation(args)} pending — your ask stays OPEN until an answer "
                f"or verdict --re's #{n}", C_HINT))


def deliver_wakes(args, base, sender, to, n, mtype="note", origin=None):
    """Nudge every recipient's pane. Wakes stay BEST-EFFORT (P22) — the log is the only truth.

    A wake is only ever ATTEMPTED for a recipient with an ACTIVE roster row AND a pane. Every
    other recipient is SKIPPED: never woken, never written to the log, named to the sender in
    the one summary line with the reason. Only an attempted wake can fail, so `> delivery-failure`
    means exactly what P22 says it means. Before this, an unreachable recipient produced a
    logged 'failure' for a wake nobody ever sent — 46 such lines once buried the one real failure
    of a run, and a package with no `scientist` seat logged a phantom scientist failure on EVERY
    single send (the built-in auto-wake default naming a seat that did not exist).

    T5: the surviving wakes run in a bounded thread pool; serially, each recipient cost the
    sender 1.3s of Enter-verify (~13s for a 10-seat send-all). Results print sorted by agent, so
    output stays deterministic."""
    _, _, rows = load_workers(base)
    gmap = group_map(base)
    decls = inbox_decls(args)
    relayed = relay_seats(to, decls) if to not in gmap else frozenset()
    if to == "all":
        recipients = {r["agent"] for r in rows if r["agent"] != sender}
        label = "all"
    elif to in gmap:
        recipients = set(gmap[to]) - {sender}
        label = f"group '{to}'"
    elif relayed:
        # A relay token is resolved for the WAKE too. Addressing it without this would produce the
        # exact defect this seat was commissioned on, in its cleanest form: a message the master's
        # `read` shows and no wake ever nudged it for — the two computations disagreeing again,
        # one layer up. The label names the resolution so the wake line is self-explaining.
        recipients = set(relayed) - {sender}
        label = f"{to} ({', '.join(sorted(relayed))})"
    else:
        recipients = {to}
        label = to
    # The built-in auto-wake names (DEFAULT_AUTO_WAKE/DEFAULT_OBSERVERS) are a DEFAULT, not a
    # roster: they join only where THIS package actually knows the name (a roster row or a
    # briefing). A default name absent from the package produces no wake, no skip mention and no
    # log line — it is not a recipient of this run at all. Briefing-DECLARED auto-wake seats are
    # by construction in the briefings, so they are unaffected.
    observers, auto_wake = observer_sets(args)
    known = {r["agent"] for r in rows} | set(briefing_frontmatters(workers_dir(args)))
    recipients |= (auto_wake & known) - {sender}

    # G-20/G-21: the wake half of the inbox scope. A message the seat's `read` will not show it
    # must not cost it a wake either — waking a seat to fetch nothing is the pure-overhead version
    # of the very interruption this bounds. Filtered seats are NAMED to the sender with the reason,
    # exactly as every other skipped recipient is (T3): the sender always learns who did not get
    # the nudge and why, so a narrowed inbox is never silent at either end.
    closing = {seat: entry for seat, entry in load_closing(base).items()
               if closing_entry(base, seat) is not None}
    # The CLOSING cut keeps its own per-branch rules verbatim — G-21 semantics are a STATE
    # machine, not a visibility question, and folding them into the predicate would have changed
    # which closing seats a group message reaches. Only the VISIBILITY test below is unified.
    # `origin` rides along so the wake's visibility test is asked of the SAME message the log
    # records. Without it a cross-package send would be judged local here and foreign at read —
    # the two computations disagreeing about one message, which is the class this seat owns.
    pending = {"sender": sender, "to": to, "type": mtype, "origin": origin}
    scope_skipped = {}
    closed_out = set()
    if to == "all":
        closed_out = {n for n in recipients if n in closing}
    elif to in gmap:
        # G-32: an observer or auto-wake seat pulled in from OUTSIDE the group still reads the
        # message by grant, so its closing cut is the direct-message rule, not the member rule.
        members = set(gmap[to])
        closed_out = {n for n in recipients
                      if closing.get(n) is not None
                      and (n in members or not closing_reaches(n, sender, closing[n]))}
    else:
        closed_out = {n for n in recipients
                      if closing.get(n) is not None
                      and not closing_reaches(n, sender, closing[n])}
    for name in sorted(closed_out):
        scope_skipped.setdefault("closing", []).append(name)
    # G-20/G-21/G-101 — and the fix this seat was commissioned for: the wake half now asks the
    # SAME question `read` asks, instead of re-deriving a weaker one per branch. The bare direct
    # branch had no visibility test at all, so `auto-wake: yes` bought a seat an interruption for
    # every direct message in the room and a `read` that showed it none of them. `closing` is
    # passed empty because the branch above already ruled on it.
    for name in sorted(set(recipients) - closed_out):
        if not shows_in_inbox(pending, name, gmap, observers, "any", (), decls):
            scope_skipped.setdefault(
                why_not_woken(pending, name, gmap, observers, decls), []).append(name)
    for names in scope_skipped.values():
        recipients -= set(names)

    # T1: the wake embeds the identity-less form — the recipient's own pane/env resolves it.
    text = (f"[coord wake] New coordination message #{n} from {sender} to {label}. "
            f"Read it now, then continue your task: {coord_invocation(args)} read")
    targets, skipped, failures = [], dict(scope_skipped), []
    nonmembers = addressable_nonmembers(args, base)[0]
    for name in sorted(recipients):
        row = current_row(rows, name)
        if name in nonmembers:
            # NOT "not launched" — that reason implies a pane is coming. This one never is, and the
            # sender must be able to tell a seat that has not started from a correspondent that is
            # never woken by design.
            skipped.setdefault("PULL delivery — addressable NON-MEMBER, no pane in this run; it "
                               "reads the log itself", []).append(name)
        elif row is None:
            skipped.setdefault("not launched", []).append(name)   # briefed/named, no row yet
        elif row["active"] != "yes":
            skipped.setdefault("departed", []).append(name)       # had a row, checked out/closed
        elif not is_tmux_pane(row["pane"]):
            # F1: either no pane at all, or a PANELESS (daemon-lane) row bound to a session id.
            # Both are pull-delivery seats — they read the log at their own checkpoints.
            skipped.setdefault("no pane", []).append(name)
        elif at_approval_gate(row["pane"]):
            # 8(b) blind-gate hygiene: the seat is alive but parked on an interactive approval
            # modal. Typing into it cannot be read and can land INSIDE the modal's input — the
            # broadcast would corrupt the very gate leader has to answer. Same skip semantics as
            # every other unreachable recipient (T3): not woken, not logged, NAMED to the sender
            # with the reason, so leader knows to run `approve` rather than assume delivery.
            skipped.setdefault("at an approval gate", []).append(name)
        else:
            targets.append((name, row["pane"]))

    def one(target):
        name, pane = target
        ok, err = wake(pane, text)
        return name, pane, ok, err

    results = []
    if targets:
        with ThreadPoolExecutor(max_workers=min(WAKE_PARALLEL_MAX, len(targets))) as pool:
            results = list(pool.map(one, targets))
    delivered = 0
    for name, pane, ok, err in sorted(results):
        if ok:
            delivered += 1
            continue
        failures.append(f"{name} ({pane}): {err or 'tmux send-keys failed'}")
    # T6: a 20-seat broadcast printed 20 result lines the sender had to scan for the one that
    # mattered. Wakes are best-effort chrome — the counts are ONE line, and only failures (the
    # actionable half) keep a line of their own. Skipped seats are named, not just counted:
    # the sender still has to know which seats did not get the nudge, and why.
    parts = [f"{delivered} delivered"]
    if failures:
        parts.append(f"{len(failures)} failed")
    # The tuple fixes the ORDER of the reasons worth leading with; the trailing pass catches any
    # reason not named in it. Before that pass a skip reason absent from this list was computed,
    # applied, and never printed — the seat was silently not woken and the sender was told
    # nothing, which is precisely the silent-drop this summary exists to prevent. A hard-coded
    # list of what may be reported is a list of what can vanish.
    ordered = ("departed", "not launched", "no pane", "at an approval gate",
               "special-case seat", "not in its inbox", "closing")
    for why in ordered + tuple(w for w in sorted(skipped) if w not in ordered):
        names = skipped.get(why)
        if names:
            parts.append(f"{len(names)} skipped ({why}: {', '.join(sorted(names))})")
    print("  wakes: " + (", ".join(parts) if (delivered or failures or skipped)
                         else "no live recipient panes"))
    for line in sorted(failures):
        print(f"  wake FAILED -> {line}")
    gated = skipped.get("at an approval gate")
    if gated:
        print(c(f"  next: {', '.join(sorted(gated))} is parked on an approval prompt — leader "
                f"clears it with {coord_invocation(args)} approve <agent>, and the seat picks this "
                f"message up on its next read", C_HINT))
    if failures:
        log_delivery_failures(base, failures)
        print(f"  ({len(failures)} delivery failure(s) recorded in the log — recipients must "
              f"pick the message up via `read` at their next checkpoint)")


def render_message(b, superseded_by):
    print(c(b["lines"][0], TYPE_COLOR.get(b["type"], "")))
    if b["num"] in superseded_by:
        # P12 — the retraction travels WITH the claim, so no reader acts on a withdrawn one.
        print(c(f"*** SUPERSEDED by #{superseded_by[b['num']]} — do not rely on this message ***",
                C_RETRACT))
    body, notes = split_log_notes(b)
    print("\n".join(body).rstrip())
    if notes:
        print()
    for note in notes:
        # Set apart from the body, never hidden: this is the log's own record of a wake that
        # did not arrive, not something the sender wrote.
        print(c(f"[log] {note}", C_LOGNOTE))
    print()


def digest_line(b, superseded_by):
    """One line per message (T2): enough to triage a 300-message log without reading it."""
    marks = ""
    if b["supersedes"] is not None:
        marks += f" (supersedes #{b['supersedes']})"
    if b["re"] is not None:
        marks += f" (re #{b['re']})"
    ts = b["ts"].split(" ")[-1] if b["ts"] else "--:--"
    num_col = "{:<4}".format("#" + str(b["num"]))
    type_col = "{:<10}".format(b["type"])
    retracted = (c(f" [SUPERSEDED by #{superseded_by[b['num']]}]", C_RETRACT)
                 if b["num"] in superseded_by else "")
    return (f"{c(num_col, C_LABEL)} {ts} {c(type_col, TYPE_COLOR.get(b['type'], ''))} "
            f"{b['sender']}->{b['to']}{marks}{retracted}  {truncate(body_of(b))}")


def persist_cursor(base, agent, target):
    """Store the read cursor. NEVER fatal (F9): a codex seat's sandbox makes the package
    read-only (EROFS) and a concurrent writer can lose the os.replace race — either way the
    reader keeps the messages it was just shown and gets an `--after` hint instead of a
    traceback. The no-op guard skips the rewrite entirely when the cursor would not move: that
    rewrite was itself a race source (scientist-roster #103). Returns (stored, note)."""
    try:
        with coord_lock(base):
            path, lines, rows = load_workers(base)
            row = current_row(rows, agent)
            if row is None or row["active"] != "yes":
                return False, "no active check-in"
            if row["lastread"] == str(target):
                return True, "unchanged"
            row["lastread"] = str(target)
            lines[row["_line"]] = row_text(row)
            atomic_write(path, "".join(lines))
        return True, ""
    except (OSError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def cmd_read(args):
    """Bounded, cursor-safe inbox read (T2 + the designer catch).

    The cursor advances ONLY on an unfiltered, non-peek read, and only through the LAST MESSAGE
    SHOWN. Before this, a filtered read (`--type ask` — leader's documented drain) advanced the
    cursor past every non-matching message, silently dropping it from that agent's inbox
    forever; and an unbounded read dumped a 300-message log into the reader's context."""
    base = base_dir(args)
    me = resolve_agent(args)
    # task 7.93 — the gateway read leg. INERT unless COORD_GATEWAY_TRANSPORT=1 (criterion 4).
    # Placed HERE, before the local render's several exit paths, so it is reached on every one of
    # them — including the `no messages yet` return, which is exactly the case where a message
    # sitting on the daemon plane and nowhere else would otherwise be invisible.
    gateway_read_leg(args, base, me)
    _, blocks = load_messages(base)
    if not blocks:
        print("no messages yet")
        return
    gmap = group_map(base)
    _, _, wrows = load_workers(base)
    row = current_row(wrows, me)
    observers, _ = observer_sets(args)
    superseded_by = {b["supersedes"]: b["num"] for b in blocks if b["supersedes"] is not None}
    addressed = getattr(args, "addressed", "any")
    digest = getattr(args, "digest", False)
    msg = getattr(args, "msg", None)
    coord = coord_invocation(args)

    if msg is not None:
        b = next((x for x in blocks if x["num"] == msg), None)
        if b is None:
            refuse(
                "state",
                f"no message #{msg} in the log — it ends at #{blocks[-1]['num']}.\n"
                f"List what is there: {coord} read --digest --all",
                1)
        render_message(b, superseded_by)
        if b["re"] is not None:
            print(c(f"-- answers ask #{b['re']}", C_HINT))
        settled = [x["num"] for x in blocks if x["re"] == b["num"]]
        if settled:
            print(c("-- answered by #" + ", #".join(str(s) for s in settled), C_HINT))
        print(c("-- peek: --msg never moves your cursor", C_HINT))
        return

    # P26 — persisted cursor: default start point is the agent's stored last-read.
    if args.all:
        start = 0
    elif getattr(args, "after", None) is not None:
        start = args.after
    else:
        start = int(row["lastread"]) if row and row["lastread"].isdigit() else 0

    filtered = (args.type is not None) or (addressed != "any")
    closing = closing_seats(base)      # hoisted: the withheld pass below needs the same set
    decls = inbox_decls(args)
    candidates = [b for b in blocks
                  if b["num"] > start
                  and shows_in_inbox(b, me, gmap, observers, addressed, closing, decls)
                  and (args.type is None or b["type"] == args.type)]
    # G-94 — A SILENT FILTER AND AN EMPTY INBOX ARE THE SAME OUTPUT, and that is what made the
    # defect permanent rather than merely late: `read` answered "no new messages for leader" while
    # a run-1 -> run-2 LEADER LIFECYCLE HANDOVER sat in the log, then advanced the cursor past it,
    # so no later read ever re-offered it. Recovery needed `--msg N`, which a reader with an
    # empty-looking inbox has no reason to run.
    #
    # Reported here is the ONE bucket that is both dangerous and always small: messages whose `to`
    # NAMES THIS SEAT and which the inbox predicate cut anyway. The broad "not addressed to you"
    # count is deliberately NOT reported — in a busy room it is most of the log, and a footer that
    # announces the room's whole traffic every read would re-import the very context a bounded
    # inbox exists to keep out, burying this signal in the noise it creates.
    withheld = [b["num"] for b in blocks
                if b["num"] > start and b["to"] == me
                and not shows_in_inbox(b, me, gmap, observers, addressed, closing, decls)]
    limit = getattr(args, "limit", None)
    if limit is None:
        limit = 0 if args.all else READ_LIMIT  # --all = deliberate full replay
    limit = max(0, limit)
    shown = candidates[:limit] if limit else candidates
    remaining = len(candidates) - len(shown)
    tail = blocks[-1]["num"]

    if not shown:
        print(f"no new messages for {me} after #{start}")
    for b in shown:
        if digest:
            print(digest_line(b, superseded_by))
        else:
            render_message(b, superseded_by)
    if digest and shown:
        print()
    print(c(f"-- shown {len(shown)} message(s); last message number in log: {tail}", C_HINT))
    if withheld:
        nums = ", ".join(f"#{n}" for n in withheld[:8])
        more = f" (+{len(withheld) - 8} more)" if len(withheld) > 8 else ""
        print(c(f"-- {len(withheld)} message(s) ADDRESSED TO YOU were withheld by the inbox filter: "
                f"{nums}{more}. Read any of them in full with `{coord} read --msg N` — this line "
                f"exists because an inbox that filters silently reads exactly like an empty one "
                f"(G-94)", C_HINT))
    if remaining:
        print(c(f"-- {remaining} more waiting — run `{coord} read` again", C_HINT))
    # Only asks nobody has settled yet — pointing the reader at an ask that already has its
    # answer is worse than saying nothing (the derivation is `open_asks`, same as `pending`).
    open_nums = {b["num"] for b in open_asks(blocks)}
    asked = [b for b in shown if b["type"] == "ask" and b["num"] in open_nums]
    if asked:
        first = asked[0]
        print(c(f"next: answer what is yours — {coord} send {first['sender']} \"<answer>\" "
                f"--type answer --inline --re {first['num']}", C_HINT))

    advance = not (args.peek or args.all or digest or filtered)
    if not advance:
        why = ("--peek" if args.peek else "--all" if args.all else "--digest" if digest
               else "a filtered read (--type/--addressed) shows only part of your inbox")
        print(c(f"-- peek semantics: this read did NOT move your cursor ({why}). Run a plain "
                f"`{coord} read` to actually drain your inbox.", C_HINT))
        return
    if not shown:
        print(c(f"-- cursor unchanged at #{start} (nothing new was shown)", C_HINT))
        return
    target = shown[-1]["num"]
    stored, note = persist_cursor(base, me, target)
    if stored and note == "unchanged":
        print(c(f"-- cursor already at #{target}", C_HINT))
    elif stored:
        print(c(f"-- cursor advanced to #{target} (override any time: --after N, --all, --peek)",
                C_HINT))
    else:
        print(c(f"-- cursor NOT stored ({note}) — the messages above are still yours; pass "
                f"--after {target} on your next read", C_HINT))


def cmd_status(args):
    """One-shot orientation (T2/F12): who am I, is my pane reachable, is the owner around, what
    is waiting for me, where is my cursor, what do I run next. Recovery used to mean `workers`
    plus `read --peek` plus a manual scan."""
    base = base_dir(args)
    me = resolve_agent(args)
    coord = coord_invocation(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    print(f"{c('you:   ', C_LABEL)} {c(me, C_LABEL)}")
    if not row or row["active"] != "yes":
        print(f"{c('roster:', C_LABEL)} {c('NOT checked in', C_DEAD)} — no active row for '{me}'")
        print(c(f"next:   {coord} checkin {me} \"<what you are working on>\"", C_HINT))
        return
    # ⚠ NO LIVENESS VERDICT HERE [T4-R8, C-15, C6, del-observers]. A pane is a viewport, never a
    # heartbeat — "is it alive" is answered only by probing the supervisor registry, not built by
    # this seat. This reports one mechanical fact only: can a WAKE reach this row's registered
    # pane through tmux right now. It never claims the seat itself is alive, dead, or "ok".
    live = live_panes()
    if not row["pane"]:
        pane_state = "no pane registered — wakes cannot reach you; run `read` at your own checkpoints"
    elif not is_tmux_pane(row["pane"]):
        # F1: paneless (daemon-lane) row — bound to its session id, not to tmux. Not a defect.
        pane_state = "paneless — bound to your session id, not a tmux pane; run `read` yourself"
    elif live and row["pane"] not in live:
        pane_state = "not in tmux's current pane list — a wake sent to it will not be delivered"
    else:
        # No live tmux server means live_panes() is empty and every registered pane reads the
        # same as one tmux currently reports — an honest degradation, the same one `workers` makes.
        pane_state = "registered"
    print(f"{c('pane:  ', C_LABEL)} {row['pane'] or '-'} ({pane_state})")
    print(f"{c('work:  ', C_LABEL)} {truncate(row['summary'], 120)}")
    print_owner_status(base, label_width=7, args=args)
    _, blocks = load_messages(base)
    tail = blocks[-1]["num"] if blocks else 0
    cursor = int(row["lastread"]) if row["lastread"].isdigit() else 0
    waiting = unread_for(args, base, me, cursor)
    counts = {}
    for b in waiting:
        counts[b["type"]] = counts.get(b["type"], 0) + 1
    breakdown = ", ".join(f"{c(k, TYPE_COLOR.get(k, ''))} {v}"
                          for k, v in sorted(counts.items())) or "none"
    print(f"{c('cursor:', C_LABEL)} #{cursor} of #{tail} in the log")
    print(f"{c('unread:', C_LABEL)} {len(waiting)} ({breakdown})")
    gmap = group_map(base)
    # `set()` for observers is DELIBERATE and survives the unification: an observer reads the whole
    # log by grant, and "asks waiting on YOU" must stay the asks it must personally answer, not
    # every open ask in the room. What changes is that the composition `sender != me AND
    # addressed_to` is no longer re-spelled here — this was the FIFTH site to derive that pair by
    # hand, and re-deriving one predicate in five places is exactly the drift that let the wake half
    # and the read half disagree for two fixes without either being wrong on its own.
    # Same hoist as in `unread_for`: both are per-block re-reads of the whole descriptor set.
    _closing, _decls = closing_seats(base), inbox_decls(args)
    mine = [b for b in open_asks(blocks)
            if shows_in_inbox(b, me, gmap, set(), "any", _closing, _decls)]
    # A narrowed inbox must never be invisible to the seat living in it: a seat that sees fewer
    # messages than the room is sending has to be able to tell "filtered by design" from "the
    # wakes are broken", and the second is a real failure mode this run has already hit.
    scope_line = inbox_scope_line(base, me)
    if scope_line:
        print(f"{c('inbox: ', C_LABEL)} {scope_line}")
    # The SENDER bound, which the line above never carried — and the omission was not neutral: for
    # a bounded seat that line asserts "direct messages always reach you", which is the opposite of
    # true. `me` is the identity the CLI resolved for THIS caller; there is deliberately no way to
    # ask for another seat's (G-197, and see inbox_bound_line).
    bound_line = inbox_bound_line(me, inbox_decls(args),
                                  [w["agent"] for w in launch.discover_workers(workers_dir(args))])
    if bound_line:
        print(f"{c('senders:', C_LABEL)} {bound_line}")
    detail = ("  " + ", ".join(f"#{b['num']} from {b['sender']} ({age_of(b['ts'])})"
                               for b in mine[:5])) if mine else ""
    print(f"{c('asks waiting on you:', C_LABEL)} {len(mine)}{detail}")
    # Surfaced on EVERY seat's status, not only the leader's roster view: a refused monitor flag is
    # the run failing to warn itself, and the seat it was about is often the one that most needs to
    # see it. Tonight's two crossings were about the leader and the chief-of-staff, and neither
    # ever learned a warning had been raised.
    _und = undelivered_line(base)
    if _und:
        print(c(_und, C_DEAD))
    # s3-04, the twin site. Surfaced on EVERY seat's status for the reason the line above carries:
    # a stuck lifecycle is the run failing to finish an act it started, and the seat it is ABOUT is
    # often the one that most needs to see it. Until Stage 4's revival arm lands, these two prints
    # are the ONLY readers the marker has.
    _lcl = lifecycle_exec.lifecycle_line(base)
    if _lcl:
        print(c(_lcl, C_DEAD))
    if waiting:
        print(c(f"next:   {coord} read", C_HINT))
    elif mine:
        print(c(f"next:   {coord} pending", C_HINT))
    elif me == "leader":
        # Leader has nobody to escalate to — the idle hint told it to `send leader`, i.e. to
        # message itself. Leader's idle move is draining the run's queue: open asks first
        # (`pending` also shows broadcast asks and its own unanswered ones), then the log.
        print(c(f"next:   {coord} pending — drain the run's open asks, then {coord} read",
                C_HINT))
    else:
        print(c(f"next:   continue your task ({coord} send leader \"<msg>\" --type ask --inline when "
                f"blocked)", C_HINT))


def cmd_pending(args):
    """Open asks, computed over the FULL log — not cursor-relative (T4/F11)."""
    base = base_dir(args)
    me = resolve_agent(args)
    coord = coord_invocation(args)
    _, blocks = load_messages(base)
    gmap = group_map(base)
    opens = open_asks(blocks, base=base)
    # G-94: `pending` derives open asks over the FULL log, so a foreign seat sharing my role name
    # put its own asks in "your asks nobody has answered" and hid its asks TO me. Same one
    # predicate as read and the wake half — a view that answers "is this mine" differently from
    # the inbox is the drift this class is named for.
    to_me = [b for b in opens if not is_own_send(b, me)
             and (b["to"] == me or (b["to"] in gmap and me in gmap[b["to"]]))]
    broadcast = [b for b in opens if not is_own_send(b, me) and b["to"] == "all"]
    from_me = [b for b in opens if is_own_send(b, me)]
    # G-leader-0823-0238 (task 92/134 sibling gap): none of the four sections above can render an
    # ask addressed to `owner` BY ANOTHER SEAT unless the reading seat happens to be `owner` itself
    # or the ask was broadcast to `all` — a peer's `to: owner` ask matched neither `to_me` nor
    # `broadcast`, so it was invisible to `pending` no matter who ran it (stools ask #251,
    # `audio-live-prober` -> owner, invisible while `pending` printed zero). A halt that cannot be
    # shown is as bad as one silently cleared, so this section renders regardless of who is asking.
    to_owner = [b for b in opens if b["to"] == OWNER_TOKEN and b not in to_me]

    def section(title, items, hint, colour="ask"):
        print(f"{c(title, C_LABEL)} ({len(items)})")
        if not items:
            print("  (none)")
            return
        for b in items:
            num_col = "{:<4}".format("#" + str(b["num"]))
            age_col = "{:>4}".format(age_of(b["ts"]))
            print(f"  {c(num_col, TYPE_COLOR[colour])} {age_col} old  {b['sender']}->{b['to']}  "
                  f"{truncate(body_of(b))}")
        print(c(f"  {hint}", C_HINT))

    # W4 (adv, C47) — an unanswered ESCALATION is a halt, and it sits in the nag view until somebody
    # settles it. FIRST, above the asks: it is the one row here that means the run is stopped.
    section("UNANSWERED ESCALATIONS — the run is halted on these", open_escalations(blocks),
            "these wait on the OWNER. Nothing here times out and nothing auto-proceeds; "
            "settle one with an answer carrying --re <#>",
            colour="escalation")
    section("open asks to the owner", to_owner,
            "these wait on the OWNER too — settle one with an answer carrying --re <#>")
    section("asks waiting on you", to_me,
            f"answer one: {coord} send <sender> \"<answer>\" --type answer --inline --re <#>")
    section("open asks to everyone", broadcast, "answer only what is yours to answer")
    section("your asks nobody has answered", from_me,
            "chase the recipient, or retract with --supersedes <#>")


# ── task 7.93 · the gateway transport legs (owner ruling `r-793-unbarred-slot-address-door`) ────
#
# The daemon gained an addressed-message door: intent `send-message` {type, thread, corpus}, and
# `inspect messages` addressable BY THREAD. The ADDRESS is the thread (D39/D42) and NO recipient
# column is minted anywhere — `d-team-kit-realization`'s divergences 1 and 4 STAND, so the CLIENT
# is adapted to the gateway's shape rather than the gateway being taught a recipient.
#
# ⚠⚠ OPT-IN, AND INERT BY DEFAULT — the leader's 7.57 fork-2 ruling, and criterion 4 of this row.
# `armed()` is FALSE unless COORD_GATEWAY_TRANSPORT is exactly "1", and every leg below returns
# immediately when it is false, BEFORE resolving a workspace, reading a file, or opening a socket.
# Detection alone NEVER arms it: a naive detect-then-route would flip the transport for every seat
# mid-run, on the file whose half-save downs the room. It is deliberately an ENV switch rather than
# a CLI flag because criterion 3 requires the agent-facing surface (checkin/send/read/pending) to
# stay UNCHANGED — no new flag appears on any of them.
#
# ⚠ THE LOCAL APPEND-ONLY LOG REMAINS THE ROOM'S SUBSTRATE and is untouched by these legs. The
# daemon row carries (type, sender, thread, corpus) and nothing else, while the room's header
# additionally carries `to`, `supersedes`, `re`, `why`, `origin` and an exec stamp — the fields
# every refusal, cursor, wake and ask-closure in this file is computed from. A cutover would
# DELETE them, which is exactly the substrate fact `d-team-kit-realization` rules permanent. So
# the gateway is an ADDITIONAL carrier of the message plane, and what it buys is the thing that is
# impossible today in both directions: a sender with no access to this room's filesystem can write
# to a seat's address, and a seat's message becomes visible on the daemon plane.
GATEWAY_TRANSPORT_ENV = "COORD_GATEWAY_TRANSPORT"


def gateway_transport_armed(env=None):
    """True ONLY when the transport is explicitly armed. Any other value — unset, "0", "true",
    "yes" — is OFF: an opt-in that a typo can arm is not opt-in."""
    env = os.environ if env is None else env
    return env.get(GATEWAY_TRANSPORT_ENV) == "1"


def gateway_transport_target(args):
    """(host, port, token) for the armed transport, or None when no daemon serves this workspace.
    Never raises for an ordinary absence — an unarmed or unserved workspace is not an error."""
    root = gateway_client.resolve_workspace_root(VAULT_ROOT)
    # `resolve_gateway_addr`, NOT `detect_daemon`: it honours an explicit IGNITE_GATEWAY_ADDR and
    # falls back to the machine-keyed server.json record, which is the same resolution order the
    # reference JS client uses. `detect_daemon` answers only the second question, and a transport
    # that ignored the explicit address would be unable to reach a gateway an operator named.
    try:
        host, port = gateway_client.resolve_gateway_addr(root)
    except gateway_client.GatewayUsageError:
        return None
    # E22: the token walk (env, then `.rbtv/config/sender-token.env` up from the cwd) also tries the
    # workspace root — from a seat folder bound below an ro-masked `seats/`, the cwd walk alone
    # cannot reach it. A read-root seat sees that file; the cage never masks it.
    return host, port, gateway_client.resolve_token(workspace_root=root)


def gateway_thread_for(args, base, to):
    """The slot/groupchat address this room's `to` maps to. One home for the arithmetic, so the
    send leg and the read leg can never disagree about where a message went (PRIN-11)."""
    return gateway_client.thread_address(
        package_dir(args).name, to, is_group=(to in group_map(base)))


def gateway_send_leg(args, base, to, mtype, body):
    """Carry a just-appended message through the door. Returns None on success or when the
    transport is not armed; returns a FAILURE STRING otherwise — never silence.

    ⚠ A FAILED LEG NEVER READS AS A SENT ONE (task 7.94's discipline, applied to this leg): the
    caller prints the returned string loudly and exits non-zero, so a seat can never believe the
    daemon plane carried a message it refused."""
    if not gateway_transport_armed():
        return None
    try:
        target = gateway_transport_target(args)
    except gateway_client.GatewayUsageError as exc:
        return f"gateway transport is ARMED but its configuration is unusable: {exc}"
    if target is None:
        return (f"gateway transport is ARMED but no daemon serves this workspace — the message is "
                f"in the local log ONLY. Unset {GATEWAY_TRANSPORT_ENV} or install ignite here.")
    host, port, token = target
    # `completion` is not carried by this door: it needs a status the door has no field for, and
    # the daemon refuses it explicitly. Skipped rather than sent-and-refused, so an ordinary
    # completion never produces a false failure line.
    #
    # W4 decides the new types' carriage EXPLICITLY rather than letting the enum decide by default:
    #   · `queue-request` JOINS the skip list. It is ENGINE-INTERNAL — the consumer W7 builds reads
    #     the local bus, not the daemon plane — so crossing this door buys nothing and puts a row
    #     nobody drains on a second substrate.
    #   · `escalation` CROSSES. It is owner-directed, and the daemon plane is how it reaches a
    #     human; that is why the four JS enum copies had to move in this same change.
    # D2 decides its own type the same way, EXPLICITLY:
    #   · `stuck` CROSSES — it is a health signal, and the daemon plane and the heart store are
    #     where a reconciliation loop and an operator view can see one. It is therefore ABSENT from
    #     this skip list on purpose, and that is why the four JS enum copies and the store CHECK
    #     move in D2's change too: a door refusing a type this leg carries is the D3 silent class.
    # Spelled as a literal, NOT derived from WRITER_HELD_TYPES: that tuple empties when W7 lands a
    # consumer, and the skip is a permanent routing decision that must not empty with it.
    if mtype in ("completion", "queue-request"):
        return None
    thread = gateway_thread_for(args, base, to)
    try:
        gateway_client.send_message(host, port, thread, mtype, body, token=token)
    except (gateway_client.GatewayTransportError, gateway_client.GatewayUsageError) as exc:
        return (f"gateway leg FAILED — the message IS in the local log and was NOT carried to the "
                f"daemon plane (thread {thread}): {exc}")
    print(c(f"  gateway: carried to {thread}", C_HINT))
    return None


def gateway_read_leg(args, base, me):
    """Show what the DAEMON plane holds for this seat's address. No-op unless armed.

    This is the read half of the door: the execution-scoped form of `inspect messages` needs a
    jobs_log exec id, which a tmux seat does not have and cannot obtain — the exact finding 7.57
    fork 1 ruled NOT MET. Failures are printed, never raised: a daemon that is down must not stop
    a seat reading its own local inbox."""
    if not gateway_transport_armed():
        return
    try:
        target = gateway_transport_target(args)
    except gateway_client.GatewayUsageError as exc:
        print(c(f"gateway read leg unavailable: {exc}", C_DEAD))
        return
    if target is None:
        print(c("gateway transport is ARMED but no daemon serves this workspace — local log only.",
                C_DEAD))
        return
    host, port, token = target
    thread = gateway_thread_for(args, base, me)
    try:
        result = gateway_client.read_thread(host, port, thread, token=token)
    except (gateway_client.GatewayTransportError, gateway_client.GatewayUsageError) as exc:
        print(c(f"gateway read leg FAILED for {thread}: {exc}", C_DEAD))
        return
    rows = result.get("rows") or []
    if not rows:
        print(c(f"gateway: no messages on the daemon plane for {thread}", C_HINT))
        return
    print(c(f"gateway: {len(rows)} message(s) on the daemon plane for {thread}", C_LABEL))
    for r in rows:
        print(f"  [gateway] #{r.get('msg_id')} {r.get('created_at')} "
              f"{c(str(r.get('type')), TYPE_COLOR.get(r.get('type'), ''))} "
              f"from {r.get('sender')}: {truncate(str(r.get('corpus') or ''))}")
    print()


def cmd_gateway_status(args):
    """Task 7.57 criterion (1), the DETECT half only. Reports whether an ignite daemon
    serves THIS workspace on THIS machine (`.rbtv/modules/ignite/server.json`,
    machine-keyed, D27) — a pure file read, always safe, never opt-in.

    It does NOT route send/read through the gateway: RULED NOT MET, with the finding
    (task 7.57 fork 1) — the gateway's nine intents carry no addressed-message door.
    `checkin`/`send`/`read`/`pending`/... are UNCHANGED by this command's existence and
    never call anything in this function.

    `--probe` is the SPEAK half, and it is INERT UNLESS PASSED (Fork 2, ruled: client
    mode is opt-in, never silently switched) — it makes exactly ONE live, read-only
    `inspect` call to prove the client can authenticate to the gateway as a sender. It
    never sends or reads a coordination message; there is no door for that yet.
    """
    root = gateway_client.resolve_workspace_root(VAULT_ROOT)
    info = gateway_client.detect_daemon(root)
    print(f"workspace root: {root}")
    if info["detected"]:
        print(f"daemon detected: yes — {info['host']}:{info['port']}  ({info['reason']})")
    else:
        print(f"daemon detected: no  ({info['reason']})")
    print("coordination transport: run-package substrate (file log + flock), UNCHANGED —")
    print("  send/read/checkin/pending never route through the gateway. NOT MET (task 7.57")
    print("  fork 1): the gateway's 9 intents carry no addressed-message door — enqueue-job's")
    print("  send-message action takes exactly (type, thread, corpus), no recipient; inspect")
    print("  messages requires an integer execution id a tmux seat does not have.")
    if not getattr(args, "probe", False):
        print(c("next:   --probe to make one live read-only `inspect` call and prove the "
                 "authenticated wire", C_HINT))
        return
    if not info["detected"]:
        print("PROBE SKIPPED: no daemon detected for this workspace/machine — nothing to call.")
        sys.exit(1)
    token = gateway_client.resolve_token()
    print(f"probing {info['host']}:{info['port']} as an authenticated sender "
          f"({'token present' if token else 'NO TOKEN in env — expect AUTH_REFUSED'}) ...")
    try:
        status, envelope = gateway_client.call_gateway(
            info["host"], info["port"], "inspect", {"target": "queue"}, token=token)
    except gateway_client.GatewayTransportError as exc:
        print(f"PROBE FAILED (transport): {exc}")
        sys.exit(5)
    print(f"HTTP {status} — {json.dumps(envelope)}")
    if envelope.get("ok") is True:
        print("PROBE: authenticated call SUCCEEDED (ok:true) — the client CAN reach the "
              "gateway as an authenticated sender. This proves the WIRE only — it is not a "
              "coordination send or read, and none exists on this door yet.")
        return
    err = envelope.get("error") or {}
    print(f"PROBE: call returned ok:false — code={err.get('code')} message={err.get('message')}")
    sys.exit(3 if err.get("code") == "AUTH_REFUSED" else 1)
