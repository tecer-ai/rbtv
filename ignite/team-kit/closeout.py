import os
import re
import shlex
import signal as signal_mod
import sys
import time
from pathlib import Path

# ---------- transcript export / close / depart ----------

def transcripts_dir(args, agent):
    d = workers_dir(args) / agent / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_transcript(args, agent, label=""):
    """Capture the agent's full pane scrollback into its worker folder. Returns (path, err)."""
    _, _, rows = load_workers(base_dir(args))
    row = current_row(rows, agent)
    if not row or not row["pane"]:
        return None, f"no registered pane for '{agent}' — nothing to capture"
    text, err = tmux_capture(row["pane"])
    if err:
        return None, f"capture failed for {row['pane']}: {err}"
    suffix = f"-{label}" if label else ""
    out = transcripts_dir(args, agent) / f"{file_stamp()}-{agent}{suffix}.txt"
    out.write_text(text, encoding="utf-8")
    return out, ""


def cmd_export_transcript(args):
    out, err = export_transcript(args, args.target, args.label or "")
    if err:
        refuse(
            "environment",
            f"cannot capture '{args.target}' — {err}. A scrollback capture needs the "
            f"seat's registered pane to still exist.\nCheck the roster: "
            f"{coord_invocation(args)} workers",
            1)
    print(f"transcript exported: {out}")
    print(c(f"next: {coord_invocation(args)} close-seat {args.target} — the mechanical close, "
            f"once the memory.md this seat owes is written", C_HINT))


def renew_in_place(seat, pane, pane_live, pane_window_name=None):
    """Pure: True when a renew must RESPAWN the seat's existing pane rather than kill it and split
    a fresh one. G-12 — kill+split re-tiles the whole window, so every renew destroyed the layout
    the owner had arranged.

    THE DESCRIPTOR WINS (G-154): keep the pane when it is ALREADY where the briefing asks the seat
    to be; re-place it when it is not. Keying on placement KIND alone was correct only while no
    seat declared a window — the moment `r-window-layout` put `window:` on thirteen descriptors it
    silently switched EVERY one of them off this path, so each `close-seat --renew` began killing
    its pane. Nobody edited this function; the descriptors underneath it changed, and the run
    record went on describing renew as "respawns into the SAME pane" while it destroyed panes.

    `pane_window_name` is the window the pane is in RIGHT NOW, resolved by the caller so this stays
    pure. Omitted, a window/shared seat re-places — the pre-G-154 behaviour — so a caller that has
    not been taught to measure the window cannot silently acquire the new path."""
    if not (bool(pane) and bool(pane_live)):
        return False
    place, wname = seat_placement(seat)
    if place == "pane":
        return True                      # no window demand at all — wherever it sits is correct
    # `own`/`shared`: the briefing names a window. Respawn in place only when the pane ALREADY sits
    # in that window; otherwise this renew is also the act that moves the seat where it belongs,
    # and keeping the pane would strand it. That is what the old comment feared, correctly — it
    # just applied the fear to every window seat instead of only the misplaced ones.
    return bool(pane_window_name) and pane_window_name == wname


def cmd_close_seat(args):
    # The daemon or leader runs this directly — a live seat that is finished or near its context
    # limit, or a dead pane needing cleanup. [T2-R9] deleted the `closer-*` seat class that used to
    # run this as the tail of its own spawned close; nothing spawns a seat to call it anymore.
    #
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — `close-seat` is callable by any
    # resolved identity, closing ANY seat including a foreign one. `_caller` is still resolved,
    # never for gating, but because the W1 self-act warning right below needs to know whether the
    # caller and the target are the same seat.
    _caller = gate(args, "close-seat")
    # W1 — A WARNING, NEVER A REFUSAL. The self-act is legal and stays legal; what it is not is
    # SURVIVABLE for the caller's own turn. A self `close-seat --renew` respawns the caller's own
    # pane when the seat already sits in the window its descriptor names (`renew_in_place`, and
    # G-154 is why placement decides it) and kills it outright when it does not — `tmux
    # respawn-pane -k` either way — so EVERY STEP AFTER THIS COMMAND NEVER RUNS. That is not
    # hypothetical: the "checkout kills its own pane" fix was REFUSED for destroying the in-place
    # renew path, and the selftest still carries that ratification (G-134's row).
    # This warning is load-bearing between Stage 1 and Stage 3: Stage 1 makes the self-act LEGAL,
    # Stage 3 supplies the out-of-pane executor that makes it SURVIVABLE. Until then the caller is
    # told, every time, which path was built for this.
    if _caller and _caller == args.target:
        print(c(f"WARNING self-act: '{_caller}' is closing ITSELF. This kills or respawns your own "
                f"pane" + (" (--renew respawns it in place only if you already sit in the window "
                           "your descriptor names)" if getattr(args, "renew", False) else "") +
                f", so every step you had planned after this command will NEVER RUN.\n"
                f"The path built for this is `{coord_invocation(args)} checkout --renew` — it "
                f"hands off and lets the seat come back without destroying the turn that asked.",
                C_DEAD), file=sys.stderr)
    base = base_dir(args)
    # A DOOR IS NOT CLOSED MECHANICALLY. A seat declaring `relays:` carries the relay path to a
    # HUMAN role, and its pane is the surface that human is watching — the owner can be sitting at
    # it while the seat itself is checked out.
    #
    # G-151, corrected: this comment used to read "renew here does not respawn in place — it kills
    # and re-creates", generalised from ONE measurement (leader #385). That reading was true of the
    # seat measured and false as a general claim, and it sat thirty lines from `renew_in_place`'s
    # docstring saying the opposite — a contradiction inside one file that two rulings then leaned
    # on from opposite sides, each correct from where it stood. Both were describing the SAME
    # decision from different seat classes. What is actually true: the plain close ALWAYS kills the
    # pane; the renew kills it too UNLESS the seat is already in the window its briefing asks for
    # (G-154), in which case the pane is kept and respawned. This early check cannot tell which
    # case it is in — `in_place` is not computed until later — and it does not need to: a door is
    # not closed mechanically on EITHER branch.
    #
    # REFUSED, NOT SILENTLY EXEMPTED: unlike `reap`, this command is an explicit deliberate act, so
    # the right answer is to make the caller say they mean it rather than to ignore the request.
    # `--force` is that, and it is the same escape every other refusal in this file offers.
    #
    # Derived from the descriptor, extending the predicate reap already uses — not a second list.
    if not getattr(args, "force", False):
        _relays = ((inbox_decls(args).get(args.target) or {}).get("relays"))
        _row = current_row(load_workers(base)[2], args.target)
        _pane = (_row or {}).get("pane") or ""
        if _relays and _pane and _pane in live_panes():
            refuse(
                "state",
                f"'{args.target}' carries a relay path to a human role "
                f"({', '.join(sorted(_relays))}), and its pane {_pane} is LIVE. A plain close "
                f"kills that pane; a --renew kills it too unless the seat is already in the "
                f"window its briefing asks for (G-154), and you cannot tell which case you are "
                f"in from here. So this may close the door a human is watching, possibly while "
                f"they are away and expecting it to be there.\n"
                f"A door in the wrong place is cosmetic; a door destroyed is an outage.\n"
                f"If you mean it (the run is ending, or the owner has moved): --force",
                1)
    if not args.no_export:
        out, err = export_transcript(args, args.target, "close")
        print(f"transcript: {out}" if not err else f"transcript skipped — {err}")
    _, _, rows = load_workers(base)
    row = current_row(rows, args.target)
    # Resolved BEFORE anything is killed: the in-place decision needs the seat's placement, and
    # the pids to verify dead are only readable while the pane still exists (G-10).
    seats = ([w for w in discover_workers(workers_dir(args)) if w["agent"] == args.target]
             if args.renew else [])
    # G-51: checked BEFORE the seat is closed, not after. A renew that refuses halfway has already
    # killed the pane — the seat would be gone AND not relaunched, which is worse than either
    # outcome the check is choosing between. This is the exact path the run's live divergence sits
    # on: `close --renew` reads the DESCRIPTOR, so a registry re-bind never reaches it.
    if seats:
        check_bindings(args, seats, "close --renew")
    old_pane = (row or {}).get("pane") or ""
    old_idents = pane_harness_idents(old_pane) if old_pane else []
    # G-154: the window the pane is in RIGHT NOW is measured here, not inferred, because that is
    # the only thing that can say whether the seat is already where its briefing wants it.
    in_place = bool(seats) and renew_in_place(seats[0], old_pane, old_pane in live_panes(),
                                              tmux_pane_window_name(old_pane) if old_pane else None)
    if row and row["active"] == "yes":
        def close_row(r):
            r["active"] = "no"
            r["checkout"] = f"closed {now()}"

        update_row(base, args.target, close_row)
        print(f"roster: {args.target} closed")
    # 7.37: the session row is COMPLETED wherever the roster row goes inactive — this is one of
    # the three such paths (close-seat, depart, checkout). Idempotent: a seat with no open row
    # gains nothing, so a depart followed by a close-seat writes one `ended`, not two.
    sid, cerr = session_trace_safe(session_close, args, args.target)
    if cerr:
        print(c(f"WARNING sessions.csv row NOT completed — {cerr}. The close itself stands.",
                C_DEAD), file=sys.stderr)
    elif sid:
        print(f"sessions.csv: {sid} ended")
    # G-21: the state dies WITH the close, and unconditionally — including the renew path, where
    # the successor is a fresh seat that must boot with a full inbox, and including a close-seat
    # run directly by leader on a dead pane, which never had its own renewal arm it to clear. A closing flag
    # that outlives its seat would quietly filter a live successor's messages, which is the failure
    # this whole change exists to prevent, wearing the other mask.
    if clear_closing(base, args.target):
        print(f"inbox: '{args.target}' closing state cleared — the narrowing does not outlive the "
              f"close")
    # G-134: the debt is settled by the act that actually frees the resources. Cleared here rather
    # than at the kill below so the RENEW path clears it too — an in-place renew keeps the pane
    # deliberately (G-12), and a debt left standing for a seat that is back and running would make
    # the record lie in the opposite direction.
    # W1/F3 — THE `incomplete` ENTRY SURVIVES A PLAIN CLOSE, and it is the only value that does.
    #
    # WHAT THE WIPE COST. `incomplete` is the seat's own statement that its work is unfinished.
    # Clearing the live entry here used to erase it while the durable row was still empty; the
    # ledger is now written at checkout, but the live entry still carries route/handoff/debt
    # `close-seat` reads, so an `incomplete` is kept until relaunch.
    #
    # ⚠ THE RENEW ARM STILL WIPES, AND THE EXCEPTION IS LOAD-BEARING (adv, C5, G-134's own reason).
    # A renew brings the seat straight BACK: the successor is live, checked in and working, and a
    # stale `incomplete` sitting in the live surface beside its fresh session row is DISPOSITION
    # SKEW — two records of one seat's ending that disagree — which parks every reader until a
    # human adjudicates. A renewed seat's ending is the successor's to declare.
    _aw_entry = load_awaiting(base).get(args.target)
    _aw_disp = (_aw_entry.get("disposition", "done") or "").strip() if isinstance(_aw_entry, dict) else ""
    if _aw_disp == "incomplete" and not args.renew:
        print(f"awaiting close: '{args.target}' entry KEPT — it carries the seat's own "
              f"`incomplete`, the honest ending this close does not get to erase. It clears when "
              f"the seat is relaunched (the relaunch admission clears it) or when a leader rules "
              f"the row.")
    elif clear_awaiting(base, args.target):
        print(f"awaiting close: '{args.target}' debt settled")
    old_window = ""
    if old_pane:
        old_window = tmux_pane_window(old_pane)
        if in_place:
            print(f"pane {old_pane}: KEPT for an in-place renew — respawned below, so the "
                  f"window layout survives (G-12)")
        else:
            ok, err = tmux_kill_pane(old_pane)
            print(f"pane {old_pane}: {'killed' if ok else 'kill failed — ' + err}")
            # G-10: kill-pane SIGHUPs the process group and a blocked harness survives it as a
            # ghost the roster never mentions. Confirm the exit; escalate rather than assume.
            survivors, note = verify_pids_gone(old_idents)
            if old_idents:
                print(f"process check: {len(old_idents)} harness pid(s) "
                      + (f"GONE{' — ' + note if note else ''}" if not survivors
                         else f"NOT gone — {note}"))
    if args.renew:
        if not seats:
            print(f"renew FAILED: no briefing in {workers_dir(args)} carries "
                  f"`agent: {args.target}`, so there is nothing to relaunch — the seat is closed "
                  f"but not renewed.\nRelaunch it by hand once the briefing exists: "
                  f"{coord_invocation(args)} launch --only {args.target}", file=sys.stderr)
            sys.exit(1)
        # A pane seat relaunches into the window its old pane occupied (if it survived the
        # kill) — e.g. a renewed leader lands back in the control panel — NEVER the caller's
        # own window, so a leader running this on a foreign seat cannot accidentally strand
        # the renewed seat there. Window/shared seats re-place from their briefing as before.
        launch_target = ""  # a tmux pane, not an agent — args.target is the seat being renewed
        if in_place:
            launch_target = old_pane
        elif seat_placement(seats[0])[0] == "pane" and old_window and tmux_session_name(old_window):
            launch_target = old_window
        if not launch_target:
            launch_target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
        if not launch_target:
            print(f"renew FAILED: the seat is closed, but relaunching it needs a tmux window and "
                  f"this shell is not inside tmux (no $TMUX_PANE) — its old window is gone too.\n"
                  f"Relaunch it from leader's pane: {coord_invocation(args)} launch --only "
                  f"{args.target}", file=sys.stderr)
            sys.exit(1)
        # A renewed seat re-reads its rules at boot, so it needs a current mirror just as a
        # fresh launch does — and a renew lands mid-run, exactly when sources have been drifting.
        refresh_mirrors_for(seats[:1])
        tmux_raise_history_limit()
        same_cell = None
        if in_place:
            ok, rerr = tmux_respawn_pane(old_pane, seats[0]["cwd"])
            if ok:
                same_cell = old_pane
                survivors, note = verify_pids_gone(old_idents)
                if old_idents:
                    print(f"process check: {len(old_idents)} harness pid(s) "
                          + (f"GONE{' — ' + note if note else ''}" if not survivors
                             else f"NOT gone — {note}"))
            else:
                # Fall back to the old kill+split path rather than stall the renew: a re-tiled
                # window is a cosmetic loss, a seat that never comes back is not.
                print(f"respawn-in-place failed ({rerr}) — falling back to kill+split, which "
                      f"re-tiles this window", file=sys.stderr)
                tmux_kill_pane(old_pane)
                verify_pids_gone(old_idents)
                launch_target = old_window or launch_target
        pane, err = launch_seat(seats[0], args, launch_target, pane=same_cell)
        if err:
            print(f"renew FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"renewed: {args.target} relaunched in {pane}"
              + (" (same pane, layout intact)" if same_cell else "")
              + " (reads its updated memory.md at boot)")
    print(c(f"next: {coord_invocation(args)} workers — confirm the seat is "
            f"{'back and checked in' if args.renew else 'gone from the live rows'}", C_HINT))


def cmd_panel(args):
    """(leader) open the control-panel overview pane in the caller's window.

    The leader window is the run's control panel: leader + the oversight seats (watcher,
    scientist, scientist-roster) + on-demand closers as panes, plus this pane running the live
    tmux-overview of the whole session. Idempotent: skips if an 'overview' pane already exists."""
    gate(args, "panel")
    target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
    if not target:
        refuse(
            "environment",
            "panel splits a strip into the CALLING tmux window and this shell is not "
            "inside tmux (no $TMUX_PANE).\nRun it from leader's own pane.",
            1)
    for pid, title in tmux_window_panes(target):
        if title == "overview":
            print(f"overview pane already open ({pid}) — nothing to do")
            return
    session = tmux_session_name(target)
    if not session:
        print(f"panel FAILED: tmux does not resolve a session for this pane ({target}), and the "
              f"overview needs a session name to watch.\nRun it from a pane inside the run's own "
              f"tmux session.", file=sys.stderr)
        sys.exit(1)
    tool = Path(__file__).resolve().parent / "tmux-overview"
    pane, err = tmux_split_strip(target, VAULT_ROOT)
    if not pane:
        print(f"panel FAILED: {err}", file=sys.stderr)
        sys.exit(1)
    set_pane_title(pane, "overview")
    ok, terr = wake(pane, f"bash {shlex.quote(str(tool))} {shlex.quote(session)} --compact "
                          f"--package {shlex.quote(str(package_dir(args)))}")
    print(f"overview strip {pane} ({PANEL_STRIP_ROWS} rows) running tmux-overview '{session}' "
          f"--compact (roster names from the package): {'ok' if ok else 'FAILED ' + terr}")
    print(c(f"next: {coord_invocation(args)} launch — the strip tracks the seats it opens",
            C_HINT))


def cmd_reap(args):
    """One sweep pass over the awaiting-close debt: observe, confirm, and — only with --go — free.

    OBSERVES BY DEFAULT AND SAYS SO. `reap` kills panes, so the destructive form is the one that
    must be typed, not the safe one. A bare `reap` reports the debt and records this pass's
    observation; `--go` is what kills. That also makes the two-pass rule cheap to satisfy honestly:
    a watcher can sweep on its own cadence and the leader acts on an already-confirmed set.

    It never reaps a seat the run still owes a `close-seat`: reaping frees the PANE, and the roster
    row and session trace are finished by the close. So a reaped seat KEEPS its debt entry, with
    its pane now gone — the leader still sees it and still owes the close. Freeing memory and
    completing a lifecycle are different acts and this one does only the first."""
    # THE GATE IS ON THE CONSEQUENCE, NOT THE VERB (leader ruling, #363). It first covered the
    # whole command, including the observe pass — which destroys nothing. The cost of that lands
    # in exactly one place: a seat wanting to check the door exemption against the LIVE room had to
    # either override the gate or not verify. A gate that MANUFACTURES its own breaches, and
    # charges them to whoever is being most careful, is G-106's shape — every gate individually
    # correct, the bill sent to the seat behaving best. (This one billed its own author within the
    # hour: I overrode it to verify, which was the right act on an authority that was not mine.)
    #
    # So: observing is free, killing is gated. The refusal names `reap --go` rather than `reap`,
    # because a message that refuses the verb when only the flag is barred sends the reader looking
    # for the wrong permission.
    go = getattr(args, "go", False)
    if go:
        gate(args, "reap --go")
    base = base_dir(args)
    panes = live_panes()
    debts = awaiting_debts(base, panes)
    if not debts:
        print("no awaiting-close debt — every finished seat has been closed")
        return
    decls = inbox_decls(args)
    freed, held = [], []
    for seat, entry, age, _alive in debts:
        # ponytail: `base.parent` is the goal folder because `base_dir` builds it as
        # `<goal>/coordination`; under an explicit `--base` override it is not, and the pipe-pane
        # fallback then finds no `sessions.csv` and the gate reads the export alone — fail-closed,
        # never a crash. Upgrade path if `reap --base` ever needs the fallback: resolve the package
        # through `package_dir(args, register=False)` and handle its refusal here.
        blockers = reap_blockers(entry, age, panes, decls, seat, base.parent)
        seen, ready = confirm_reap(base, seat, blockers)
        aged = f"{age}min" if age is not None else "unknown age"
        if blockers:
            held.append(f"{seat} ({aged}): HELD — " + "; ".join(blockers))
            continue
        if not ready:
            held.append(f"{seat} ({aged}): every precondition holds, confirmed {len(seen)}/2 — "
                        f"a second pass at least {REAP_MIN_PASS_GAP_MIN}min from now decides it. "
                        f"One reading is a snapshot; two is a trend.")
            continue
        if not go:
            held.append(f"{seat} ({aged}): READY to reap ({len(seen)} confirmations) — "
                        f"pane {entry['pane']} would be freed. Re-run with --go.")
            continue
        idents = pane_harness_idents(entry["pane"])
        ok, err = tmux_kill_pane(entry["pane"])
        # G-10, same discipline every other teardown uses: kill-pane SIGHUPs the process group and
        # a blocked harness survives it as a ghost no roster row mentions. Confirm, never assume.
        survivors, note = verify_pids_gone(idents)
        freed.append(f"{seat}: pane {entry['pane']} "
                     + ("freed" if ok else f"kill FAILED — {err}")
                     + (f"; {len(idents)} harness pid(s) "
                        + ("GONE" if not survivors else f"NOT gone — {note}") if idents else ""))
    for line in held:
        print(c(f"  {line}", C_HINT))
    for line in freed:
        print(c(f"  {line}", C_ALIVE))
    if not go and any("READY to reap" in h for h in held):
        print(c(f"next: {coord_invocation(args)} reap --go — frees the panes listed READY above; "
                f"each still owes a close-seat afterwards", C_HINT))


def cmd_kill_pane(args):
    """Reap ONE pane by id directly -- the chief-of-staff's route to freeing a leaked pane when a
    raw `tmux kill-pane` is refused by the harness auto-mode classifier and `close-seat` needs a
    roster-known SEAT NAME rather than a bare pane id (task 7.91, owner-directed).

    MEASURED (leader #1580), not guessed: `coordinate launch --force` -- also a `coordinate` verb
    -- is ALSO blocked by the classifier from the chief-of-staff's pane, so wrapping a verb in
    coord.py is not by itself sufficient; `coordinate close-seat --force` PASSES from that same
    pane, and close-seat kills panes too, so killing a pane is not by itself what is refused. The
    ONE shape measured to pass while killing panes from that pane is close-seat's -- so this
    mirrors it as closely as the row allows: the same `tmux_kill_pane` + `verify_pids_gone` kill
    step, the same gate() role check, the same --force convention for a deliberate-but-risky act.
    The discriminator itself is NOT known and this does not guess one (criterion 1 is proof from
    %190, never an assumed pass from a pane that was never blocked).

    Kills the PANE ONLY -- like `reap`, never like `close-seat`: no transcript export, no roster
    row mutation, no session-trace close. A pane this frees still owes a close-seat afterwards if
    its row was ever active; freeing memory and completing a lifecycle are different acts, and this
    one does only the first (criterion 6 -- `cmd_reap`'s own docstring states the same split).

    TWO refusals are UNCONDITIONAL, no --force, ever (bars.md 4, criterion 2): the pane belongs to
    a seat whose descriptor declares `relays:` (the owner door, or any future human-contact role),
    or the pane matches no CURRENT roster row of this run at all. Both are REFUSED BY THE TOOL, not
    by convention, and both are derived from the roster + the descriptor's own `relays:` field --
    never a kit-side name list (the same derivation `inbox_decls`/`reap_blockers` already use).

    A THIRD refusal -- the pane's owning row is still `active: yes`, i.e. NOT roster-done
    (criterion 5) -- is the SAME kind of deliberate-act refusal close-seat's own door check uses,
    and shares its escape: --force, with the same "if you mean it" shape. G-196's lesson is why
    this reads the ROW's `active` field as ground truth rather than inferring aliveness from
    whether the pane is in `live_panes()` -- a pane that changed out from under a stale roster row
    must not be misread as free just because the OLD pane id looks live or dead."""
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — `kill-pane` is callable by any
    # resolved identity.
    gate(args, "kill-pane")
    target = args.pane_id
    if not target.startswith("%"):
        refuse(
            "input",
            f"'{target}' does not look like a tmux pane id (expected e.g. '%190') -- "
            f"kill-pane targets a PANE, never a seat name (that is close-seat's argument)",
            1)
    base = base_dir(args)
    _, _, rows = load_workers(base)
    current = [current_row(rows, a) for a in dict.fromkeys(r["agent"] for r in rows)]
    owner_row = next((r for r in current if r and r.get("pane") == target), None)

    if owner_row is None:
        refuse(
            "state",
            f"pane {target} matches no CURRENT roster row of this run -- kill-pane only "
            f"touches panes this run's own roster accounts for (criterion 2). If this is a "
            f"genuine leak from something else, it is not this tool's to reap. No --force lifts "
            f"this.",
            1)

    decls = inbox_decls(args)
    relays = (decls.get(owner_row["agent"]) or {}).get("relays")
    if relays:
        refuse(
            "state",
            f"pane {target} belongs to '{owner_row['agent']}', which carries a relay "
            f"path to a human role ({', '.join(sorted(relays))}) -- its pane is a DOOR, never "
            f"reapable, unconditionally (bars.md 4, r-owner-afk-liaison-parked). No --force "
            f"lifts this.",
            1)

    if owner_row["active"] == "yes":
        if not getattr(args, "force", False):
            refuse(
                "state",
                f"pane {target} belongs to '{owner_row['agent']}', whose roster row is "
                f"still ACTIVE -- not roster-done (criterion 5). A live working seat's pane is "
                f"close-seat's or renew's to manage, not a bare reap. If you mean it (the seat is "
                f"gone but the row was never closed): --force.",
                1)
        print(f"WARNING: '{owner_row['agent']}' is still roster-ACTIVE -- killing its pane anyway "
              f"because --force was given. Its roster row is UNCHANGED by this call and still "
              f"needs a close-seat.", file=sys.stderr)

    idents = pane_harness_idents(target)
    ok, err = tmux_kill_pane(target)
    print(f"pane {target} ({owner_row['agent']}): {'killed' if ok else 'kill FAILED -- ' + err}")
    if not ok:
        sys.exit(1)
    survivors, note = verify_pids_gone(idents)
    if idents:
        print(f"process check: {len(idents)} harness pid(s) "
              + (f"GONE{' -- ' + note if note else ''}" if not survivors
                 else f"NOT gone -- {note}"))
    # Criterion 4: asserted from tmux list-panes, never inferred from tmux_kill_pane's exit code
    # (which only says the COMMAND ran, not that the pane is actually gone -- G-10's whole point).
    still_there = target in live_panes()
    print(f"tmux check: pane {target} "
          + ("STILL LISTED -- the kill did not take" if still_there else "GONE"))
    if still_there:
        sys.exit(1)
    print(c(f"next: {coord_invocation(args)} workers -- '{owner_row['agent']}' still shows in the "
            f"roster{' (was still active)' if owner_row['active'] == 'yes' else ''}; it still owes "
            f"a close-seat to finish its lifecycle", C_HINT))


def cmd_terminate_pid(args):
    """Terminate ONE process named by pid, under the leader's authorization, with that
    authorization written to the coordination log (task 7.153, G-303).

    THE GAP THIS CLOSES IS AN AUTHORITY WITH NO INSTRUMENT, not a missing permission. `G-303`
    measured it twice in one sitting: the chief-of-staff holds OPEN verbs only, so stopping a
    non-seat process it had started SECONDS EARLIER routed to the leader as a hand `kill` — an act
    outside every ruled procedure, unreplayable and unaudited. `kill-pane` cannot serve it: both
    processes were DETACHED with no pane, unreachable by a pane verb under any identity
    (`p-reap-stray-closed-run-watch-loop` clause (b)). So the fix could not be a widening of who
    may act; it had to be a command that PERFORMS the act the leader was already authorized to
    perform, and records it.

    ⚠ NON-SEAT RADIUS BY CONTRACT (criterion 3 arm C). A pid at or below ANY current roster row's
    pane is REFUSED, unconditionally, no --force. This is not caution — it is the boundary that
    makes the verb safe to hand a leader: every seat-directed act has its own lifecycle command
    (`close-seat`, `reap`, `kill-pane`, `depart`) which does the roster, transcript and session-
    trace work this one deliberately does not. A verb that could reach both would be a second,
    careless path to closing a seat.

    ⚠ AND THE RADIUS FAILS SAFE. `seat_radius_pids` returns `verifiable=False` when the process
    table or tmux cannot be read, and this REFUSES on it. An unreadable world would otherwise
    render an empty radius, i.e. "no pid belongs to a seat" — the guard reporting maximum
    permission at the moment it can see least.

    THE TARGET IS NAMED, NEVER INHERITED (the row's own constraint). There is no "current process",
    no environment variable, no default. A pid arrives as an argument or the command does not run.
    `--starttime` is offered because a pid ALONE is not an identity (`process_identity`): the
    kernel recycles pids, and the gap between the leader MEASURING a pid and typing this command is
    exactly the window in which one is reused. Supplying it turns a stale pid into a refusal
    instead of a stranger's death.

    NO SILENT ESCALATION. It sends the ONE signal it was asked for and then checks. A TERM that
    does not take is reported and exits non-zero (criterion 2); it does not become a KILL the
    caller never named. `verify_pids_gone` escalates because a pane teardown must complete; an
    authorized single terminate must instead do exactly what was authorized."""
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — `caller` is still resolved (never
    # gated) because the authorization record below names who ran this act.
    caller = gate(args, "terminate-pid")
    pid = args.pid
    if pid <= 1:
        refuse(
            "input",
            f"'{pid}' is not a terminable pid — 1 is init and anything below it is a process "
            f"GROUP or an error, never one named process. terminate-pid takes exactly one pid.",
            1)

    ident = process_identity(pid)
    if ident is None:
        refuse(
            "state",
            f"pid {pid} does not exist (no readable /proc/{pid}/stat) — nothing was signalled and "
            f"nothing was recorded. Re-measure the pid at the instant of use (`ps -eo "
            f"pid=,args=`); a pid carried from an earlier reading names a stranger as often as a "
            f"corpse.",
            1)
    if args.starttime and args.starttime != ident[1]:
        refuse(
            "state",
            f"pid {pid} is LIVE but its /proc starttime is {ident[1]}, not the {args.starttime} "
            f"you measured — the pid was recycled between your reading and this call, so it now "
            f"names a DIFFERENT process. Refusing: this is the exact case --starttime exists to "
            f"catch.",
            1)

    snap = ps_snapshot()
    if not snap:
        refuse(
            "environment",
            "the process table could not be read (`ps` returned nothing), so neither the "
            "self-kill guard nor the seat radius can be evaluated. Cannot-tell is not "
            "not-a-seat, and this verb refuses rather than kill blind.",
            1)
    if os.getpid() in descendant_pids(snap, pid):
        refuse(
            "state",
            f"pid {pid} is this very process or an ancestor of it — terminating it would kill "
            f"`coordinate` mid-act, before the authorization record is written. The record is not "
            f"decoration: an unrecorded terminate is the hand kill this verb replaces.",
            1)

    radius, verifiable = seat_radius_pids(args)
    if not verifiable:
        refuse(
            "environment",
            "the SEAT RADIUS could not be established — the process table or tmux could not be "
            "read for this run's roster panes. This verb is non-seat-radius BY CONTRACT and "
            "cannot honour that contract against a world it cannot see, so it refuses. An "
            "unreadable radius is never an empty one.",
            1)
    if pid in radius:
        seat, pane = radius[pid]
        refuse(
            "state",
            f"pid {pid} belongs to seat '{seat}' (pane {pane}) — terminate-pid is NON-SEAT-radius "
            f"by contract and no --force lifts this. A seat is ended through its own lifecycle: "
            f"`close-seat {seat}` (transcript + roster + session trace), or `kill-pane {pane}` if "
            f"only the pane must be freed. Killing a seat's pid from here would leave its roster "
            f"row, its debt and its trace all claiming a process that no longer exists.",
            1)

    cmdline = next((argv for p, _, argv in snap if p == pid), "(argv unreadable)")
    sig = signal_mod.SIGKILL if args.signal == "KILL" else signal_mod.SIGTERM
    base = base_dir(args)

    # ⚠ THE RECORD IS WRITTEN BEFORE THE SIGNAL, and the order is the point. It is an AUTHORIZATION
    # record, not a receipt: it says who licensed this act, against what, and why — all of which is
    # true the instant before the kill and stays true whether or not the kill takes. Written after,
    # it would be lost by exactly the failure that most needs a record (the terminate that killed
    # something it should not have, or the one that took `coordinate` down with it). The OUTCOME is
    # a second record below, tied to this one by `re:`.
    auth_n = append_message(
        base, caller, "all", "note",
        f"AUTHORIZATION — terminate-pid. Authorized by: {caller} (resolved identity, not an "
        f"asserted one: `terminate-pid` is leader-gated and this name is what the gate admitted).\n"
        f"target pid: {pid} · starttime: {ident[1]} · signal: SIG{args.signal}\n"
        f"target argv: {cmdline}\n"
        f"non-seat radius: CHECKED — the pid is at or below no current roster row's pane "
        f"({len(radius)} pid(s) in the seat radius at this instant).\n"
        f"reason: {args.reason}\n"
        f"This record is written BEFORE the signal. The outcome follows as its own entry.")
    print(f"authorization recorded as message #{auth_n} (authorized by: {caller})")

    ok, err = signal_pid(pid, sig)
    if not ok:
        append_message(base, caller, "all", "note",
                       f"OUTCOME — terminate-pid {pid}: the signal could NOT be sent ({err}). "
                       f"Nothing was terminated.", re_num=auth_n)
        refuse("environment",
               f"SIG{args.signal} could not be sent to pid {pid}: {err}. The authorization is on "
               f"the log as #{auth_n}; the process is untouched.", 1)
    print(f"SIG{args.signal} sent to pid {pid} ({cmdline[:80]})")

    # Gone is asserted from /proc, never from os.kill's silence — os.kill returns None for a
    # delivered signal a process is free to ignore, and `terminate-pid` claiming a kill it did not
    # make is the one lie a terminate verb must never tell (S5, and G-10's shape at pid scale).
    deadline = time.time() + PID_EXIT_TIMEOUT
    while time.time() < deadline and process_identity(pid) == ident:
        time.sleep(0.3)
    survived = process_identity(pid) == ident

    append_message(
        base, caller, "all", "note",
        f"OUTCOME — terminate-pid {pid} (SIG{args.signal}, authorized by {caller}): "
        + (f"the process SURVIVED {PID_EXIT_TIMEOUT}s and is still live. NOTHING was escalated: "
           f"this verb sends the signal it was asked for and no other."
           if survived else "the process is GONE, verified from /proc, not from the signal call."),
        re_num=auth_n)

    if survived:
        print(f"process check: pid {pid} is STILL LIVE {PID_EXIT_TIMEOUT}s after SIG{args.signal} "
              f"— NOT terminated. No escalation was performed.")
        print(c(f"next: {coord_invocation(args)} terminate-pid {pid} --signal KILL --reason "
                f"\"<why SIGTERM was not enough>\" — a deliberate second act, never this one's "
                f"silent second half", C_HINT))
        sys.exit(1)
    print(f"process check: pid {pid} is GONE (re-read from /proc, not inferred from the signal)")
    print(c(f"next: {coord_invocation(args)} read — the authorization (#{auth_n}) and its outcome "
            f"are on the log for whoever audits this", C_HINT))


def cmd_relaunch_pane(args):
    """Relaunch a seat's harness INTO A NAMED, ALREADY-REGISTERED PANE, in place (task 7.95,
    G-282) — the path `close-seat --renew` cannot take for a seat carrying `relays:`, because
    the door guard inside cmd_close_seat refuses that pane UNCONDITIONALLY once it is live,
    checked out or not (bars.md 4). This is not a weaker close-seat: it never kills anything and
    never touches that guard — it only respawns a pane that is ALREADY bare (no harness running
    in it) and ALREADY roster-done, so the worst case of a wrong call is a refusal, never a
    destroyed pane. It retires the chief-of-staff's `tmux send-keys` stopgap, which brought the
    door back with none of `launch`'s three gates behind it (criterion 3): the memory floor,
    check_bindings (G-51), and the roster/session-trace writes launch_seat always carries.

    MIRRORS THE RENEW-IN-PLACE PATH, NOT close-seat ITSELF (criterion 2): the same two
    primitives `cmd_close_seat --renew`'s in-place branch uses — `tmux_respawn_pane` then
    `launch_seat(..., pane=pane_id)` — called directly, so this command never reaches
    `cmd_close_seat` and therefore never reaches its guard, and never needs --force to do its
    job. The roster row is NOT written here: it is written by the relaunched seat's own
    subsequent `checkin`, exactly as a real renew relies on — and that checkin is not refused by
    P37 (the zombie double-checkin guard), because it lands from the SAME pane its own prior row
    (if any) already names.

    THE PANE ID IS A REQUIRED, CROSS-CHECKED INPUT (criterion 1, bars.md 3): never resolved by
    this tool from memory or by name alone — the caller reads it fresh from `coordinate workers`
    and it must match the roster's OWN latest recorded pane for the target, or this refuses
    unconditionally. A caller naming the wrong pane is exactly the failure bars.md 3 exists to
    prevent, and there is no legitimate reason to force through a mismatch: it means either the
    id is wrong or the roster is stale, and neither is fixed by acting on a pane current records
    do not attribute to this seat.

    FOUR REFUSALS carry NO --force escape, because the risk on each is silent and undoable:
      - no briefing carries this agent name — nothing to relaunch (use `launch` instead)
      - the pane id does not match the roster's own recorded pane for this agent (bars.md 3 —
        resolve it fresh)
      - the pane is not a live tmux pane at all (use `launch --only` for a fresh one)
      - the pane still holds a LIVE HARNESS PROCESS — this is not a bare pane, and respawning it
        would silently kill whatever is running there, worst case an owner mid-session; ground
        truth is read from /proc (G-10/G-11's own discipline: ask the process table, never the
        roster), so a stale-but-ACTIVE roster row cannot mask a genuinely running harness even
        under --force below
    ONE refusal IS force-escapable, matching kill-pane's own criterion-5 convention exactly: the
    roster row is still ACTIVE (not roster-done) — same "if you mean it" shape, for the same
    reason (a live seat's pane is close-seat's or renew's to manage). --force lifts ONLY this
    one; the live-harness check right after it is a separate, unconditional backstop and stays in
    force regardless — the roster can be wrong, /proc cannot be argued with.

    check_bindings (G-51) runs before any of the pane-state checks, on the dry-run path too,
    matching `cmd_launch`'s own reasoning verbatim: a dry-run exists to show what a real relaunch
    would do, and hiding a registry divergence from it would make the one command meant for
    inspection the one that lies."""
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — `relaunch-pane` is callable by
    # any resolved identity.
    seats = [w for w in discover_workers(workers_dir(args)) if w["agent"] == args.target]
    if not seats:
        refuse(
            "state",
            f"no worker briefing carries `agent: {args.target}` in "
            f"{workers_dir(args)}, so there is nothing to relaunch. This verb only revives an "
            f"already-registered seat into its own pane; a seat with no briefing has never had "
            f"one.",
            1)

    if args.dry_run:
        gate(args, "relaunch-pane")
    else:
        launch_gates(args, "relaunch-pane", 1)

    # G-51, on the dry-run path too (see docstring) — check_bindings does not special-case
    # dry_run itself; it refuses on a real divergence regardless.
    check_bindings(args, seats, "relaunch-pane")

    if not args.pane_id.startswith("%"):
        refuse(
            "input",
            f"'{args.pane_id}' does not look like a tmux pane id (expected e.g. "
            f"'%501') -- relaunch-pane targets a PANE, never a bare number or a seat name.",
            1)

    base = base_dir(args)
    _, _, rows = load_workers(base)
    row = current_row(rows, args.target)
    recorded = (row or {}).get("pane") or ""
    if recorded != args.pane_id:
        refuse(
            "state",
            f"{args.pane_id} does not match the roster's own recorded pane for "
            f"'{args.target}' ({recorded or 'none on record'}). Resolve the pane fresh with "
            f"`{coord_invocation(args)} workers` (bars.md 3 -- never recall a pane id) and "
            f"retarget. No --force lifts this: a mismatch means either the id is wrong or the "
            f"roster is stale, and neither is fixed by acting on a pane current records do not "
            f"attribute to this seat.",
            1)

    if row["active"] == "yes":
        if not getattr(args, "force", False):
            refuse(
                "state",
                f"'{args.target}'s roster row is still ACTIVE -- not roster-done. A "
                f"live seat's pane is close-seat's or renew's to manage, not a bare relaunch. "
                f"If you are certain the row is stale (the seat is gone but was never closed): "
                f"--force.",
                1)
        print(f"WARNING: '{args.target}' is still roster-ACTIVE -- relaunching into its pane "
              f"anyway because --force was given. Its roster row is unchanged by this call.",
              file=sys.stderr)

    if args.pane_id not in live_panes():
        refuse(
            "environment",
            f"{args.pane_id} is not a live tmux pane -- there is nothing to relaunch "
            f"into. If the pane is genuinely gone, use `{coord_invocation(args)} launch --only "
            f"{args.target}` to open a fresh one instead.",
            1)

    live_idents = pane_harness_idents(args.pane_id)
    if live_idents:
        refuse(
            "environment",
            f"{args.pane_id} still holds a live harness process "
            f"({', '.join(str(p) for p, _ in live_idents)}) -- this is not a bare pane, and "
            f"respawning it would silently kill whatever is running there, with no undo. No "
            f"--force lifts this. If that process is a stuck registration, tear it down "
            f"properly first: {coord_invocation(args)} close-seat {args.target}.",
            1)

    seat = seats[0]
    if args.dry_run:
        cmd, _err = harness_command(seat, prompt_path=(base_dir(args) / "prompts" /
                                                        f"{seat['agent']}-<stamp>.txt"))
        print(f"[dry-run] would respawn {args.pane_id} and start {seat['agent']} "
              f"({seat['harness']}/{seat['model'] or 'plan-default'}) in it, in place: "
              f"{cmd if cmd else '(harness_command refused -- see validate_seat)'}")
        return

    # A relaunch reads current rules just as a fresh launch does — it lands mid-run, exactly
    # when sources have been drifting (mirrors cmd_close_seat's own renew branch).
    refresh_mirrors_for(seats[:1])
    tmux_raise_history_limit()
    ok, rerr = tmux_respawn_pane(args.pane_id, seat["cwd"])
    if not ok:
        refuse(
            "environment",
            f"respawn of {args.pane_id} FAILED -- {rerr}. Nothing was started; verify "
            f"at tmux capture-pane -p -t {args.pane_id} before retrying.",
            1)
    pane, err = launch_seat(seat, args, args.pane_id, pane=args.pane_id)
    if err:
        print(f"relaunch FAILED: {err}\nThe pane was respawned but the harness never verified "
              f"up -- capture it: tmux capture-pane -p -t {args.pane_id}", file=sys.stderr)
        sys.exit(1)
    relays = (inbox_decls(args).get(args.target) or {}).get("relays")
    print(f"relaunched: {args.target} back up in {pane} (same pane, in place)"
          + (f" -- carries relays: {', '.join(sorted(relays))}; the door is up again"
             if relays else ""))
    print(c(f"next: {coord_invocation(args)} workers -- confirm '{args.target}' checked back in "
            f"on {pane}", C_HINT))


def cmd_depart(args):
    """Self-service exit: export own transcript, check out, kill own pane. SELF ONLY (T1) —
    it takes no target, so no seat can depart another; leader cleans dead seats with
    close-seat."""
    base = base_dir(args)
    me = resolve_agent(args)
    out, err = export_transcript(args, me, "depart")
    print(f"transcript: {out}" if not err else f"transcript skipped — {err}")
    _, _, rows = load_workers(base)
    row = current_row(rows, me)
    if row and row["active"] == "yes":
        def close_row(r):
            r["active"] = "no"
            r["checkout"] = now()

        update_row(base, me, close_row)
        print(f"checked out: {me}")
    sid, cerr = session_trace_safe(session_close, args, me)   # 7.37: a self-departure is still a closed session
    if cerr:
        print(c(f"WARNING sessions.csv row NOT completed — {cerr}. The close itself stands.",
                C_DEAD), file=sys.stderr)
    elif sid:
        print(f"sessions.csv: {sid} ended")
    # G-21: a seat that departs under its own steam mid-close (or one whose close-seat never ran)
    # must not leave its closing flag behind for a future occupant of the name.
    clear_closing(base, me)
    # G-134: a departure frees its OWN resources — it kills its pane below and arms a reaper for
    # any ghost — so it owes nothing and must not leave a debt behind. This also covers the
    # checkout-then-depart order: the entry checkout wrote is settled by the act that made it moot.
    clear_awaiting(base, me)
    pane = (row or {}).get("pane") or detect_pane(None)
    if pane:
        # G-10: kill-pane SIGHUPs the process group; a harness blocked elsewhere survives as a
        # ghost holding ~450 MB that no roster row mentions. This process dies WITH the pane, so
        # it cannot check afterwards — a detached reaper outlives both and finishes the job.
        idents = pane_harness_idents(pane)
        if idents:
            print(f"arming the exit reaper for harness pid(s) "
                  f"{', '.join(str(p) for p, _ in idents)} — no ghost survives this departure "
                  f"(it fires only on an exact pid+starttime match, so a recycled pid is safe)")
            arm_pid_reaper(idents)
        print(f"killing own pane {pane} — goodbye")
        tmux_kill_pane(pane)
    else:
        print("no pane to kill (not inside tmux)")


# ── D49.1 / D49.3 — `secret-add`: client of the out-of-cage daemon write ─────────────────────
#
# CLI surface stays this verb. Identity is stamped here by the F-8 ladder (pane / COORD_AGENT /
# cgroup→roster), never trusted from `--as`. This process validates and authorizes, then POSTs
# {NAME, drop-file PATH} — never the value — to gateway intent `secret-add`. The daemon (uncaged)
# re-checks authority from receiver-stamped identity, reads the drop file, appends to the
# canonical env file, deletes the drop on success, and never logs the value.
#
# No `--env-file` / COORD_SECRET_ENV_FILE hatch: a caller must not redirect the append. The
# daemon may honour RBTV_IGNITE_SECRET_ENV_FILE on its OWN process env (scratch tests); a cage
# cannot set the daemon's environment.

SECRET_ADD_MASTERS = ("goal-master", "channel-master", "console-master")
SECRET_ADD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _drop_under_goals(path):
    parts = Path(path).resolve().parts
    for i in range(len(parts) - 1):
        if parts[i] == ".rbtv" and parts[i + 1] == "goals":
            return True
    return False


def _secret_add_authority(args):
    """Admit only a proven master / uncaged console. Never a bare `--as`."""
    claimed = (getattr(args, "as_agent", None) or "").strip()
    pane = detect_pane(getattr(args, "pane", None))
    registered = ""
    if pane:
        try:
            registered = pane_agent(base_dir(args), pane)
        except (SystemExit, OSError):
            registered = ""
    actual = (registered or os.environ.get("COORD_AGENT", "").strip()
              or daemon_exec_identity())
    try:
        sid, seat = carrier_corroborated_seat(args)
    except (SystemExit, OSError):
        sid, seat = "", ""
    if not actual and sid and seat:
        actual = seat
    if claimed and claimed in SECRET_ADD_MASTERS:
        if actual != claimed:
            refuse(
                "identity",
                f"you claimed '{claimed}' (--as) to add a secret. That claim is admitted only when "
                f"your proven identity (pane, COORD_AGENT, or cgroup→roster) IS '{claimed}'. You "
                f"resolve to '{actual or 'an uncaged console'}'. There is no --force for this one.",
                2)
        return actual
    if actual in SECRET_ADD_MASTERS:
        return actual
    if not actual and not sid:
        return "console-master"
    refuse(
        "role gate",
        f"secret-add is a master act ({', '.join(SECRET_ADD_MASTERS)} / owner console). "
        f"You resolve to '{actual or 'nothing'}'. Workers cannot add secrets.\n"
        f"{ROLE_GATE_LAYER_NOTE}",
        2)


def cmd_secret_add(args):
    """Ask the daemon to append NAME from a drop file. Value never read here, never printed."""
    _secret_add_authority(args)
    name = (args.name or "").strip()
    if not SECRET_ADD_NAME_RE.match(name):
        refuse("input",
               "NAME must be a shell env identifier: letters, digits, underscore, not starting "
               "with a digit. The value is never taken from argv.", 2)
    drop = Path(args.from_file).expanduser()
    if not drop.is_file():
        refuse("input", f"drop file does not exist or is not a file: {drop}", 2)
    drop_res = drop.resolve()
    if _drop_under_goals(drop_res):
        refuse("input",
               f"drop file is under .rbtv/goals/ — live goal ledgers are not a mailbox. "
               f"Leave the file where it is. path: {drop_res}", 2)
    target = gateway_transport_target(args)
    if not target:
        refuse("environment",
               "secret-add needs a running daemon serving this workspace (or IGNITE_GATEWAY_ADDR). "
               "The write is performed out-of-cage by the daemon, never by this process.", 2)
    host, port, token = target
    try:
        status, envelope = gateway_client.secret_add(
            host, port, name, str(drop_res), token=token)
    except gateway_client.GatewayTransportError as exc:
        refuse("environment", f"secret-add could not reach the daemon: {exc}", 2)
    if not isinstance(envelope, dict):
        refuse("environment", f"secret-add: daemon returned a non-object envelope: {envelope!r}", 2)
    if envelope.get("ok") is True:
        result = envelope.get("result") or {}
        env_path = result.get("env_file") or "the workspace env file"
        print(f"secret-add: appended {name} to {env_path}")
        if result.get("drop_consumed"):
            print(f"secret-add: consumed drop file {drop_res}")
        else:
            print(f"secret-add: appended, but failed to delete drop file {drop_res} — owner must remove it")
        return
    err = envelope.get("error") or {}
    code = err.get("code") if isinstance(err, dict) else None
    msg = err.get("message") if isinstance(err, dict) else repr(err)
    text = msg or f"daemon refused secret-add ({code or 'UNKNOWN'})"
    if code == "UNAUTHORIZED_SENDER":
        refuse("role gate", text, 2)
    if "already exists" in text:
        refuse("state", text, 2)
    if ".rbtv/goals/" in text:
        refuse("input", text, 2)
    refuse("environment", text, 2)


