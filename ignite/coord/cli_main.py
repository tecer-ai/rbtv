
def add_identity_flags(s, force=True):
    """--as / --force are also accepted AFTER the subcommand (that is where agents type them).
    SUPPRESS leaves the global --as untouched when the subcommand's copy is absent."""
    s.add_argument("--as", dest="as_agent", default=argparse.SUPPRESS, metavar="NAME",
                   help="act as this agent instead of the resolved identity")
    if force:
        s.add_argument("--force", action="store_true",
                       help="override this command's refusal (identity mismatch, validation)")


def add_pretty_flag(s):
    """`--pretty` on the four VIEW commands as well as globally — that is where a human types it
    (`coordinate status --pretty`). SUPPRESS keeps the global value when this copy is absent."""
    s.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS,
                   help="ANSI colour + aligned columns (also: COORD_PRETTY=1); default is plain")


# T6/F2 — the top-level help used to print this module's docstring: a ~120-line manual that
# listed every subcommand a second time and had already drifted from the code. It is now a
# grouped 1-line-per-command index; each command's own -h carries the detail, an example and the
# step that follows. Global flags are summarised in the footer instead of an options block —
# argparse renders one line per flag, and the whole point of this help is that it fits on a
# screen. Groups are LIFECYCLE-ordered, not alphabetical.
#
# ONE EPILOG PER DOOR. The `coordinate` surface is what every working seat types; the remedial
# and launch surface is `supervise`'s, and each door's help lists only what that door accepts
# (owner ruling 2026-08-25). Every command's one-line description below is the SAME text it
# carried as one CLI — the split regrouped the index, it rewrote no verb's help.
HELP_EPILOG = """everyday
  checkin     register this session — binds this tmux pane to your agent name
  status      where you stand: identity, pane, owner, unread, cursor, open asks
  read        your unread messages, {limit} at a time (cursor persisted per agent)
  send / verdict / escalate / fail-status / queue-requests  message one agent, a group, or all — typed, their pane woken · dod-judge trial verdict: append the row the escalation gate counts (the verb composes its first line) and check the bar in the same act · the escalation alone: append the ONE row, addressed `owner`, once the consecutive-FAIL count reaches its bar · read-only: that count, the resolved bar and where it came from · read-only: this goal's `queue-request` rows, the ENGINE's door (keys decomposed, superseded requests and superseded verdicts filtered)
  pending     open asks: waiting on you, open to everyone, yours unanswered
  rule-guard / checkout  record YOUR OWN seat's value for a guard a live `after` member reads — the seat named in the (seat, key) pair writes it, no other seat may, --source mandatory (--go; reports bare) · end your session, exports your transcript first — REFUSED while a declared output or a guard you owe is missing, or an ask of yours to the owner is unanswered; --renew --handoff hands this seat to your own next session

the goal's own record
  finish-goal / advance-state / execution  FIRE THE FINISH EDGE: the one act that finishes the goal and stops every watcher · stamp ONE append-only row on the goal's state cursor (state.csv), session-id resolved from your open row · print (or --mint) this goal's dated EXECUTION STAMP

the room
  owner / secret-add  set owner presence: present | reachable | afk · append one env NAME from a drop file (masters; value never logged)
  create-group       open a message group for one workstream
  add-to-group / remove-from-group  join or drop an existing group's members
  panel       open the control-panel overview strip in this window

other
  workers / gateway-status  who is alive and on what · is a daemon serving this workspace (--probe proves the wire)
  export-transcript  capture a seat's pane scrollback into its worker folder
  depart      ephemeral seats: export + check out + kill your own pane
  selftest    built-in self-test (temp dir, no tmux)
global: --run TAG | --package DIR (which run) · --as NAME (act as) · --pretty (colour)
details + examples: coordinate <command> -h · --force overrides a refusal, where one exists""".format(limit=READ_LIMIT)

SUPERVISE_EPILOG = """launch
  launch / session-open  open one tmux seat per worker briefing and start its harness · open ONE already-up seat's session-trace row, for a launcher that is NOT `launch` (the daemon's spawn path)
  descriptors / boot-prompt  seat-descriptor audit · the exact boot prompt ONE seat launches on, for a launcher that is not `launch`

readiness
  ready-seats  which seats are launchable NOW, recomputed from disk (a seat is READY when every `after` predecessor checked out done)

remedy — when something is broken
  close-seat / reap / kill-pane / relaunch-pane / terminate-pid  close a seat (--renew) · free panes (--go) · reap one pane by id · respawn a seat INTO its own pane (CoS too) · terminate ONE named NON-SEAT pid, authorization recorded
  approve     answer a seat's permission prompt by sending keys to its pane
  attest-exit / route-fail  record that a one-shot harness terminated (--go; reports bare) · route a FAIL back to the receiver your seat.md declares, or to the `leader` when it declares none (--go; reports bare)

the leader's rulings — on a row it did not sit in
  accept / instruct  ACCEPT a seat's finished work: its ending becomes `done`, outputs re-checked, --anchor recorded (--go; reports bare) · RULE on a seat's ended session — one of the four leader instructions the daemon drains and applies (--go; reports bare)
global: --run TAG | --package DIR (which run) · --as NAME (act as) · --pretty (colour)
details + examples: supervise <command> -h · --force overrides a refusal, where one exists"""


# ---- the two doors, by AUDIENCE (owner ruling 2026-08-25) --------------------------------------
# "coordinate must also be split at entry point. two different systems: one for the daemon or for
# leaders (if smth broken), the other for all agents working on ignite (checkin, checkout,
# message, etc)." — the owner, console, 2026-08-25.
#
# `supervise` is that first system: the launch composer, the readiness arithmetic, the mechanical
# remedies and the death stamp — the concerns `spec-component-map` §3 homes in `supervisor/`.
# `coordinate` is the second: everything a working seat types. EVERY command below sits on exactly
# ONE door, and a command missing from this tuple is a `coordinate` command — the default is the
# agent surface, because that is the door a seat has, and a verb that silently appeared there is a
# far smaller failure than a remedial verb silently vanishing from the daemon's.
#
# ⚠ AUDIENCE, NOT MODULE HOME. `rule-guard` is defined in `supervisor/attest.py` and is an AGENT
# command: the seat named in the (seat, key) pair is the only writer of its own guard value. A
# door table derived from the module layout would have taken it away from every seat.
SUPERVISION_COMMANDS = (
    "launch", "session-open", "descriptors", "boot-prompt",
    "ready-seats", "renewal-state", "surface-refusal", "lifecycle-exec",
    "close-seat", "reap", "kill-pane", "relaunch-pane", "terminate-pid", "approve",
    "attest-exit", "route-fail",
    "instruct", "accept",
)
COORDINATION_DOOR = "coordinate"
SUPERVISION_DOOR = "supervise"
DOOR_EPILOG = {COORDINATION_DOOR: HELP_EPILOG, SUPERVISION_DOOR: SUPERVISE_EPILOG}
DOOR_USAGE = {
    COORDINATION_DOOR: "coordinate [--run TAG | --package DIR] [--as NAME] [--pretty] "
                       "<command> [args]",
    SUPERVISION_DOOR: "supervise [--run TAG | --package DIR] [--as NAME] [--pretty] "
                      "<command> [args]",
}
DOOR_DESCRIPTION = {
    COORDINATION_DOOR: "Coordination CLI for a multi-agent tmux team run — all state lives in "
                       "the run package.\nIdentity is resolved, never typed: --as NAME > "
                       "$COORD_AGENT > this pane's roster row.",
    SUPERVISION_DOOR: "Supervision CLI — the daemon's and a leader's remedial surface over a run: "
                      "launch,\nreadiness, and the acts that repair a seat. Seat-facing "
                      "coordination is `coordinate`.",
}


def door_of(name):
    """Which door accepts this command. The default is the agent surface (see the tuple above)."""
    return SUPERVISION_DOOR if name in SUPERVISION_COMMANDS else COORDINATION_DOOR

# Commands that are ACCEPTED by the parser and deliberately ABSENT from HELP_EPILOG above.
#
# The epilog IS the command list a seat reads, and the parser-vs-epilog check treats any command
# missing from it as drift — correctly, because that is how an undocumented command ships. This
# tuple is the ONE way to declare an omission as intended, and it is a tuple rather than a habit so
# the declaration is greppable and the check keeps failing for every command NOT in it.
#
# `lifecycle-exec` (s3-05) is here because no seat ever types it: `s3-09`'s caller forks it as a
# detached subprocess. It is still registered through `command()` like every other subcommand, so
# `save-coord.py`'s parser-build gate covers it and its own -h is held to the same example/next bar.
# `surface-refusal` is the seeding pass landing a cage-admission refusal on the bus (D2,
# 2026-08-19) — a daemon-only lane; no seat ever types it.
# `renewal-state` is the engine's exit decision transporting `renewal_state`'s answer (LE-10,
# 2026-08-19) — read-only, engine-consumed; no seat ever types it.
HIDDEN_COMMANDS = ("lifecycle-exec", "surface-refusal", "renewal-state")


ADVICE_SEND = re.compile(
    r'send\s+(?P<to>\{[^}]*\}|<[^>]*>|[A-Za-z0-9_.-]+)\s+\\?"(?P<body>[^"\\]*)\\?"'
    r'(?P<rest>(?:\s+--[a-z-]+(?:\s+(?!--)[^\s"]+)?)*)')
ADVICE_FLOOR = 5
_ADVICE_PLACEHOLDER = re.compile(r'^(\{.*\}|<.*>)$')


def _advice_render(n):
    """The text of a string expression, with f-string slots shown as {expr}."""
    import ast
    if isinstance(n, ast.Constant):
        return n.value if isinstance(n.value, str) else ""
    if isinstance(n, ast.JoinedStr):
        return "".join(_advice_render(v) for v in n.values)
    if isinstance(n, ast.FormattedValue):
        try:
            return "{" + ast.unparse(n.value) + "}"
        except Exception:
            return "{?}"
    if isinstance(n, ast.BinOp):
        return _advice_render(n.left) + _advice_render(n.right)
    return ""


def advice_coached_sends(path=None):
    """Every `send` this file's own advice coaches, as argv — hints, -h epilogs, refusal texts.

    G-181. The advice surface and the send guards drift apart silently: rbtv 4837088 made the
    positional-body guard UNCONDITIONAL and 14 advice strings kept teaching the shape it now
    refuses, for hours, because nothing tied the two together.

    DERIVED, NEVER ENUMERATED (G-158): sites are found by scanning, so a hint added tomorrow is
    covered without editing this function. Selftest fixtures are excluded by their enclosing
    function name — their strings are controlled inputs, not advice to a user.
    """
    import ast
    src = Path(path).read_text(encoding="utf-8") if path else PRODUCT_SOURCE
    tree = ast.parse(src)
    spans = [(n.lineno, n.end_lineno) for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and "selftest" in n.name]
    # which `send` flags take a value, asked of the PARSER — the advice string runs on into prose
    # ("--force adds them anyway, if ..."), and guessing that the next word is a value swallows
    # that prose into argv, which the parser then rejects: a false RED on a hint that was fine.
    value_flags = set()
    # …and which of those take a MESSAGE NUMBER, asked of the parser the same way (`type=int`).
    # Advice writes that value as a placeholder — `--re <#>`, `--supersedes {n}` — and the generic
    # placeholder substitution below turns it into `body`, which `type=int` then rejects: a false
    # RED on a hint that was fine, and false REDs are how correct hints get deleted (G-151). `--re`
    # carried a hardcoded exception for exactly this; DERIVING the pair instead means the next
    # numeric flag arrives covered rather than red (G-158). Found by `--supersedes`: D8's refusal
    # coached it for one sitting, this check correctly reported it as an offender, and the ruling
    # that removed that line (a parked ask no longer reaches the refusal) left the generalization
    # standing on its own — it is a property of the parser, not of the advice that surfaced it.
    msgnum_flags = set()
    for act in _send_actions(build_parser()):
        if act.nargs != 0 and getattr(act, "const", None) is None:
            value_flags.update(o for o in act.option_strings if o.startswith("--"))
            if act.type is int:
                msgnum_flags.update(o for o in act.option_strings if o.startswith("--"))

    outer = []

    class _V(ast.NodeVisitor):
        def visit_JoinedStr(self, n):
            outer.append(n)

        def visit_Constant(self, n):
            if isinstance(n.value, str):
                outer.append(n)

        def visit_BinOp(self, n):
            if _advice_render(n):
                outer.append(n)
            else:
                self.generic_visit(n)

    _V().visit(tree)

    sites = []
    for node in outer:
        text = _advice_render(node)
        if not text or any(a <= node.lineno <= b for a, b in spans):
            continue
        for m in ADVICE_SEND.finditer(text):
            to = m.group("to")
            # `all` is NEVER normalised to a seat name: it is the recipient the owner hint was
            # refused for, and rewriting it would lose the only case a flag cannot fix.
            #
            # ⚠ NOR IS `auto` (D2), for EXACTLY that reason. It is the reserved token a ROUTED type
            # is addressed to, and `cmd_send` refuses a `--type stuck` that names any seat — so
            # rewriting `auto` to `beta` turns every line teaching the ruling into the one shape
            # the ruling forbids, and reports the correct advice as an offender. Measured: it did,
            # on the change that added the type. The `{AUTO_TOKEN}` SLOT form is resolved too,
            # because advice writes the constant rather than the literal.
            if to in (AUTO_TOKEN, "{AUTO_TOKEN}"):
                to = AUTO_TOKEN
            elif to != "all":
                to = "beta"
            body = m.group("body") or "body"
            if _ADVICE_PLACEHOLDER.match(body.strip()):
                body = "body"
            argv = ["send", to, body]
            toks = (m.group("rest") or "").split()
            i = 0
            while i < len(toks):
                t = toks[i]
                if not t.startswith("--"):
                    break                      # prose begins; the command ended
                argv.append(t)
                if t in value_flags and i + 1 < len(toks):
                    v = toks[i + 1]
                    argv.append("ASK" if t in msgnum_flags
                                else ("body" if _ADVICE_PLACEHOLDER.match(v) else v))
                    i += 2
                else:
                    i += 1
            sites.append((node.lineno, argv))
    return sites


# G-181 population 4: the kit's DOCS coach commands too, and protocol.md is loader step 4 for
# every seat — the highest-traffic advice surface in a run. Three of its four `send` synopsis lines
# taught the positional form the guard refuses, mis-teaching the room at BOOT.
#
# The invocation is DERIVED, never a literal: the docs write `$COORD`, and a scan keyed on
# `coordinate` returned ZERO and nearly certified them clean — verify-absence violated by the
# wrong pattern, which is the same class this whole check exists for.
# 7.570: NO `^\s*` ANCHOR, and its absence is the point. The anchor made this a LINE-START test,
# so every invocation written backtick-inline in prose — which is how `conduct.md` and
# `closer-prompt.md` teach their commands — was unreadable to the detector. Used with `.search`
# (never `.match`) at the one call site below.
#
# `\{COORD\}` IS IN THE ALTERNATION BECAUSE THE FIX WAS MEASURED, NOT ASSUMED. With recursion and
# inline matching alone, `closer-prompt.md` became REACHED AND READ and still matched NOTHING:
# it is a {TOKEN}-substituted template, so its invocations read `{COORD} send ...` and the bare
# `COORD\s+` arm dies on the closing brace. That is the SAME vacuous-guard trap this row exists
# to stop — a detector reporting clean over a document it opened and could not read — one level
# down, and it was found only by enumerating the widened detector's real hits. The two offenders
# it exposed (`closer-prompt.md` steps 5 and 8) are fixed in the same change.
ADVICE_INVOCATION = re.compile(
    r'(?:\$?COORD|\{COORD\}|coordinate|python3?\s+coord\.py)\s+', re.I)
# A doc may QUOTE a refused form in order to FORBID it, and flagging that would delete the warning
# that prevents the defect — G-176's trap one layer out. The first design keyed on negation words
# near the line. The leader found the residual and it points the DANGEROUS way — a FALSE GREEN:
#
#     Do not forget the type flag.          <- incidental "not"
#     $COORD send x "body" --type note      <- genuinely TAUGHT, silently exempted
#
# A false red wastes a seat; that loses the defect. And it is not fixed by moving the lookback:
# `# do not forget --type` on the command line itself exempts it just as well. Any negation
# heuristic can be tripped by prose that was never about this check.
#
# So the vocabulary check is replaced by an EXPLICIT MARKER — the same shape as the guard this all
# started from, where a positional body pays an explicit `--inline`. Only an assertion cures an
# inference. The marker is an HTML comment: invisible in rendered markdown, and impossible to write
# by accident, so an incidental sentence can never exempt a taught command.
ADVICE_DOC_OPTOUT = re.compile(r'<!--\s*advice-check:\s*refused-example\s*-->', re.I)


def advice_doc_sends(root=None):
    """-> (sites, skipped_as_warnings). Coached sends in the kit's own .md files, at ANY depth
    and ANYWHERE ON THE LINE.

    TAUGHT vs QUOTED-AS-WRONG: a candidate is an invocation carrying a QUOTED BODY. A doc that
    deliberately shows a refused form marks it with the explicit opt-out comment; every skipped
    line is RETURNED IN FULL, never counted, because a count in permanent output has no
    maintainer and only grows, while three lines of real text are auditable at a glance.

    ---- 7.570: THIS FUNCTION WAS BLIND TO `starter-set/conduct.md` TWICE OVER ----------------

    It is the root cause of the finding that blocked 7.546's certification: a rulebook clause
    coached an escalation to the `master` role address with a POSITIONAL BODY AND NO `--inline`,
    which the real send path refuses unconditionally, and THIS detector — built for exactly that
    class — reported clean.

    ⚠ THE OFFENDING FORM IS DESCRIBED ABOVE AND DELIBERATELY NOT REPRODUCED. The sibling CODE
    scanner `advice_refused_sends` EXECUTES every coached send it finds in this file's own
    string literals, so pasting the refused command here would make this docstring itself an
    offender and red G-181 — which is exactly what happened while this change was being written.
    Recover the verbatim clause from `git show f420519` if you need it.

    (1) It globbed `*.md` NON-RECURSIVELY, so nothing in a subdirectory was ever opened, and
        `starter-set/` is a subdirectory. Now `rglob`.
    (2) It matched only an invocation at LINE START, while both `conduct.md` and
        `closer-prompt.md` write their commands backtick-inline in prose. Now `.search` against
        an unanchored ADVICE_INVOCATION.

    ⚠⚠ WHY A GLOB-ONLY FIX WAS REJECTED, AND THIS IS THE WHOLE POINT OF THE ROW. Recursion alone
    would newly REACH `conduct.md` and still match NOTHING in it, because every command in that
    file is backtick-inline. The detector would then report CLEAN over a document it cannot
    read — strictly worse than never reaching it, since the clean report is now evidence the
    file was checked. That is the vacuous-guard class, and a glob-only fix would have
    INTRODUCED it here. This is not a judgement call: MEASURED at this HEAD, recursion alone
    buys ZERO new sites, and the inline half is what finds all three of the previously unread
    files. The two fixes ship together or neither ships; `selftest`'s 7.570 COVERAGE row pins
    that with one fixture carrying BOTH properties, so removing either half reds it.

    Sites are reported by their path RELATIVE TO `root`, not by bare filename: with recursion on,
    two different `CLAUDE.md` files exist under the kit and a bare name cannot say which one an
    offender is in.
    """
    root = Path(root or Path(__file__).resolve().parent)
    sites, skipped = [], []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not ADVICE_INVOCATION.search(line) or " send " not in f" {line} ":
                continue
            m = ADVICE_SEND.search(line)
            if not m:
                continue
            prev = next((x for x in reversed(lines[:i]) if x.strip()), "")
            if ADVICE_DOC_OPTOUT.search(line) or ADVICE_DOC_OPTOUT.search(prev):
                skipped.append((rel, i + 1, line.strip()[:90]))
                continue
            sites.append((rel, i + 1, line.strip()[:110],
                          bool(re.search(r"--inline|--file", line))))
    return sites, skipped


def _send_actions(parser):
    """The `send` subparser's actions, found by walking the parser rather than by name."""
    for act in parser._actions:
        subs = getattr(act, "choices", None)
        if isinstance(subs, dict) and "send" in subs:
            return subs["send"]._actions
    return []


def advice_refused_sends(path=None):
    """-> (offenders, total). Offenders are advice-coached sends the REAL send path refuses.

    ASSERTS THE PROPERTY, NOT THE VOCABULARY. An earlier draft checked each advice string for the
    substring `--inline`; the leader killed it with this file's own evidence — the `owner` hint was
    refused TWICE (positional body, then `a note is never an all broadcast`), so adding --inline
    turns a substring check green while the command stays refused. That detector would certify the
    exact state it exists to detect. So each command is parsed by the real parser and run through
    main()'s own boundary sequence instead, which covers any guard, including ones added later.

    VERB-SCOPED TO `send`, DELIBERATELY — the extension was MEASURED AND REJECTED, and this is the
    place that question gets asked, so the answer lives here rather than in a ledger row nobody
    opens. All 24 subcommands are coached by some advice string (~72 non-send sites against send's
    14), and NONE of them refuses: every apparent failure was extraction noise or a fixture
    artifact.

    WHY IT CANNOT BE WIDENED: `send` is extractable because THE QUOTED BODY IS A DELIMITER — the
    quotes around a body give the command an unambiguous end. Nothing else has one. Advice reads
    `close-seat <agent> --renew`, and no rule separates argv from English without
    guessing; placeholders also carry semantic constraints a generic fixture cannot satisfy (a
    group name must not collide with an agent name). Measured, a widened check flags ~28% of sites
    spuriously. A check whose only value is being trusted, wrong a quarter of the time, is WORSE
    than no check: it trains readers to ignore it, it still looks like coverage, and it RETIRES the
    human attention now covering those sites while certifying nothing.

    The unlock, if this is ever revisited, is an AUTHORING CONVENTION (commands in advice must be
    delimited), which converts guessing into parsing — a documented, owner-gated change, not a
    tweak to this function.

    ⚠ WRITING THIS DOCSTRING TRIPPED THIS CHECK, which is worth knowing before you edit it: the
    CODE scanner EXECUTES what it extracts, while advice_doc_sends() only tests for --inline/--file
    presence. So a SYNOPSIS with a metavariable — `--type T` — is fine in a .md and fails here,
    because `T` is not a real type. Illustrate with a concrete type, or the example you add to
    explain this function will be reported as an offender by it.
    """
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout

    global CLI_INVOCATION, shell_source_line, RUNS_INDEX, wake, detect_pane, live_panes
    sites = advice_coached_sends(path)
    if len(sites) < ADVICE_FLOOR:
        return None, len(sites)        # INOPERATIVE — the pattern stopped matching the source

    # G-182 — HERMETIC IN THE ENVIRONMENT, not only in the package. This used to isolate its temp
    # package and nothing else, which made it safe ONLY inside the selftest, because the selftest
    # globally stubs pane resolution and wakes. Called directly — which is how a ratifier verifies
    # a fix against a mutated copy — it inherited the caller's live pane, so the fixture roster
    # bound a fixture seat to a REAL pane and then:
    #   * every send refused "you claimed 'leader' but this pane (%N) is registered to 'beta'",
    #     11 false offenders on a WORKING file, and the leader was one message from reporting a
    #     correct fix as broken;
    #   * deliver_wakes sent real tmux keystrokes to that pane. A check that audits advice must
    #     not interrupt the room to do it.
    # The precondition existed as a COMMENT in the probe that developed this and never as code.
    # A gate that is prose is not a gate, so it is built in here and restored in `finally`.
    saved = (CLI_INVOCATION, shell_source_line, RUNS_INDEX, wake, detect_pane, live_panes)
    wake = lambda pane, text: None            # noqa: E731 — no tmux contact, ever
    detect_pane = lambda override=None: ""    # noqa: E731 — identity comes from --as, not a pane
    live_panes = lambda: set()                # noqa: E731 — no live roster to collide with
    offenders = []
    try:
        with tempfile.TemporaryDirectory() as td:
            RUNS_INDEX = Path(td) / "runs.json"
            pkg = Path(td) / "pkg"
            (pkg / "coordination").mkdir(parents=True)
            (pkg / "workers").mkdir()
            for a in ("leader", "alpha", "beta"):
                (pkg / "workers" / f"{a}.md").write_text(f"---\nagent: {a}\n---\nbrief\n")
            parser = build_parser()
            # Fixture setup must not be judged by the guard under test: the selftest replaces
            # shell_source_line with controlled lines for its own G-101 checks, and a seed send
            # refused by an inherited stub silently left the log with no ask in it — after which
            # every `--re` site failed for a reason that was this harness's, not the advice's.
            CLI_INVOCATION, shell_source_line = False, (lambda: "")

            def _run(argv):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    try:
                        main_args = parser.parse_args(
                            ["--package", str(pkg)] + argv)
                        assert_argv_body_shell_safe(main_args)
                        main_args.func(main_args)
                    except SystemExit:
                        pass

            for a in ("leader", "alpha", "beta"):
                _run(["checkin", a, "x"])
            # a REAL open ask, so `--re` binds to something: left dangling it refuses for an
            # unrelated reason, and a false RED is how a correct hint gets deleted (G-151).
            _run(["--as", "alpha", "send", "leader", "seed", "--type", "ask", "--inline"])
            # DERIVE the ask's number instead of assuming it is #1: checkins and the coached
            # sends themselves put other traffic in this log, and a `--re` pointed at a note
            # refuses for a reason that has nothing to do with the advice — a false RED, which is
            # how a correct hint gets deleted (G-151). Measured: 3 sites failed this way first.
            _, _blocks = load_messages(pkg / "coordination")
            _asks = [b["num"] for b in _blocks if b.get("type") == "ask"]
            ask_no = str(_asks[-1]) if _asks else "1"

            for lineno, argv in sites:
                argv = [ask_no if t == "ASK" else t for t in argv]
                err = io.StringIO()
                CLI_INVOCATION, shell_source_line = True, (lambda: "")
                try:
                    with redirect_stderr(err):
                        parsed = parser.parse_args(
                            ["--package", str(pkg), "--as", "leader"] + argv)
                except SystemExit:
                    offenders.append((lineno, " ".join(argv),
                                      "the parser rejects this argv"))
                    continue
                try:
                    with redirect_stdout(io.StringIO()), redirect_stderr(err):
                        # main()'s EXACT sequence: the positional-body guard runs BEFORE dispatch,
                        # not inside cmd_send. Calling cmd_send alone skipped it and passed 12
                        # sites the real CLI refuses — the check rebuilding the very class it
                        # exists to catch.
                        assert_argv_body_shell_safe(parsed)
                        parsed.func(parsed)
                except SystemExit as exc:
                    if exc.code not in (0, None):
                        first = (err.getvalue().strip().splitlines() or ["(refused)"])[0]
                        offenders.append((lineno, " ".join(argv), first[:150]))
    finally:
        (CLI_INVOCATION, shell_source_line, RUNS_INDEX,
         wake, detect_pane, live_panes) = saved
    return offenders, len(sites)


class _RefusingParser(argparse.ArgumentParser):
    """argparse's stock `error()` echoes the offending value back VERBATIM as its last line and
    exits 2. For `send`, a misplaced positional makes the MESSAGE BODY that offending value — so
    a caller piping through `2>&1 | tail -N` sees the tail of its own message where a receipt
    would be, and reads a usage error as delivery (this silently dropped every staffer send for
    50 minutes on 2026-07-31; the one line that said "error" was cropped off the TOP by tail).

    G-280 (task 7.94): the length-only truncation this class used to carry (cut past 200 chars)
    still echoed a SHORT body verbatim — and the campaign's exact repro, `send --type note --from
    leader --to owner-liaison "<body>"`, produced an `unrecognized arguments:` line under 200
    chars, so the body rode straight through. The fix is to never echo unrecognized-argument TEXT
    at all, regardless of length — only a token/char COUNT, which carries the same "something is
    wrong" signal with nothing a prose reader could mistake for their own message. The two
    properties that close the trap: (1) the offending text is suppressed, never merely truncated,
    so a message body can never appear in a failure line at any length, and (2) the LAST line is a
    layered refusal — tail keeps the END of a stream, so the refusal survives any `| tail -N`.
    On `send` specifically the refusal also says "NOT SENT" in those words (criterion 2): the
    success path prints "sent message #N", so the failure path must be equally explicit rather
    than merely lacking that line — a reader treating output as prose does not notice an absence.
    Exit stays 2 (argparse's own convention; scripted callers and watch.py key on codes)."""

    def parse_args(self, args=None, namespace=None):
        # Mirrors argparse.ArgumentParser.parse_args() exactly, except it stashes the partially
        # resolved subcommand on self BEFORE erroring on leftover args. `error()` needs to know
        # whether this refusal belongs to `send` so it can say NOT SENT (criterion 2), and by the
        # time error() runs — called from here, below — only `self` is still in scope.
        parsed, extras = self.parse_known_args(args, namespace)
        if extras:
            self._coord_failed_cmd = getattr(parsed, "cmd", None)
            self.error("unrecognized arguments: %s" % " ".join(extras))
        return parsed

    def error(self, message):
        is_send = getattr(self, "_coord_failed_cmd", None) == "send" or self.prog.endswith(" send")
        if message.startswith("unrecognized arguments:"):
            # NEVER echo the offending text — a message body can be exactly this (G-280). Report
            # only a count: enough to tell the caller something was rejected, nothing a prose
            # reader could confuse with their own content.
            offending = message[len("unrecognized arguments:"):].strip()
            message = (f"unrecognized arguments: {len(offending.split())} token(s), "
                       f"{len(offending)} char(s) — text suppressed, never echoed (a misplaced "
                       f"flag can put your message body exactly here)")
        elif len(message) > 200:
            message = message[:200] + f" ...[+{len(message) - 200} more chars cut]"
        self.print_usage(sys.stderr)
        sent_note = " Message NOT SENT." if is_send else ""
        print(refusal_text("input", f"usage error — {message}.{sent_note} NOTHING WAS SENT OR "
                           f"WRITTEN. Run `coordinate <command> --help` for the exact signature "
                           f"(send takes TWO positionals: <to> [message] — never your own name)."),
              file=sys.stderr)
        sys.exit(2)


def build_parser(door=COORDINATION_DOOR):
    """ONE door's CLI surface. Split out of main() so the self-test can render the help texts.

    Every command is registered exactly as before; the ones belonging to the OTHER door are
    registered onto a discard parser instead of this one, so each door accepts only its own
    commands while `command_parsers` still carries the whole inventory for the help audits. That
    is deliberate: the audits ask "is every command documented", which is a question about the
    tool, not about one of its doors.
    """
    p = _RefusingParser(
        prog=door,
        usage=DOOR_USAGE[door],
        description=DOOR_DESCRIPTION[door],
        epilog=DOOR_EPILOG[door],
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # -h stays, but out of the options block: with every global flag summarised in the epilog,
    # an options section holding one entry costs three lines of a help that must fit a screen.
    p.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS,
                   help=argparse.SUPPRESS)
    p.add_argument("--package", metavar="DIR", help=argparse.SUPPRESS)
    p.add_argument("--run", metavar="TAG", help=argparse.SUPPRESS)
    p.add_argument("--as", dest="as_agent", default=None, metavar="NAME", help=argparse.SUPPRESS)
    p.add_argument("--pretty", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--base", help=argparse.SUPPRESS)            # testing only
    p.add_argument("--workers-dir", help=argparse.SUPPRESS)     # testing only
    # help=SUPPRESS hides the subparsers action from the "positional arguments" block (the epilog
    # IS the command list); parsing is untouched.
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<command>", help=argparse.SUPPRESS,
                           parser_class=_RefusingParser)

    made = {}
    # Where a command registers when it belongs to the OTHER door: built, help-rendered, and
    # reachable from `command_parsers`, but not on `p` — so this door refuses it by name.
    _elsewhere = _RefusingParser(prog=door, add_help=False).add_subparsers(
        parser_class=_RefusingParser)

    def command(name, description, epilog):
        """One subcommand, onto its own door. No `help=` on purpose: the grouped epilog above IS
        the command list, and argparse would otherwise render a second, ungrouped one."""
        target = sub if door_of(name) == door else _elsewhere
        made[name] = target.add_parser(name, description=description, epilog=epilog,
                                       formatter_class=argparse.RawDescriptionHelpFormatter)
        return made[name]

    s = command(
        "checkin",
        "Register your session. This is the ONE command that carries your name: it creates your\n"
        "roster row and binds this tmux pane to you, and every later command resolves your\n"
        "identity from that binding. Run it before any briefing work, and again after a relaunch\n"
        "(a re-check-in supersedes your prior row — but is REFUSED while the pane that already\n"
        "holds this name is still alive, so a zombie relaunch cannot split a seat in two).",
        "example:\n"
        "  coordinate checkin builder \"rebuilding views/*.html from graph.py; owns views/ + "
        "render.py\"\n"
        "next: coordinate read — anything already waiting for you")
    s.add_argument("agent", help="your agent name, as in your briefing's `agent:` key — this call CREATES the pane->name binding every later command resolves")
    s.add_argument("summary", help=f"what you are working on, max {SUMMARY_MAX} chars — other agents read this line to decide whether to message you")
    s.add_argument("--pane", help="override tmux pane id (default: auto-detect from $TMUX_PANE)")
    s.add_argument("--force", action="store_true",
                   help="check in even though a LIVE pane still holds this name — only after you have confirmed the other session is dead (zombie double-launch guard)")
    s.set_defaults(func=cmd_checkin)

    s = command(
        "checkout",
        "End your session: exports your transcript, then flips your roster row to done. Run it\n"
        "when your briefing is complete and your completion message is already sent.\n"
        "\n"
        "--renew does the OPPOSITE of ending the seat: it opens the seat's NEXT session, and it is\n"
        "YOUR call, not leader's. It runs in two steps — the first arms the renewal, mutes your\n"
        "wakes and prints the second; the second carries your successor's handoff. Nothing is\n"
        "closed until that second call.\n"
        "\n"
        "--incomplete is the THIRD ending, and the honest one: your briefing asked for something\n"
        "that does not exist and is not coming. It ends the seat WITHOUT advancing anything and\n"
        "routes your reason to leader. A plain checkout is REFUSED and points you here when a\n"
        "declared output is missing, when a guard value you owe is unwritten, or when an ask of\n"
        "yours to the owner is unanswered — `done` advances the run, so it is not a word you may\n"
        "guess with. The last of those three is the one you cannot clear yourself: an answer is\n"
        "the owner's to give, so this is the way out, not a wait.",
        "example:\n"
        "  coordinate checkout\n"
        "  coordinate checkout --renew\n"
        "  coordinate checkout --incomplete \"the spec I was to review was never written\"\n"
        "next: ending for good — nothing on your side, leader runs `close-seat <you>` if the seat must\n"
        "      go; renewing — run the second call the first one printed for you")
    s.add_argument("--no-export", action="store_true", help="skip the automatic transcript export (e.g. the pane is already dead)")
    s.add_argument("--renew", action="store_true",
                   help="this checkout opens the NEXT session of this seat, not its last — run it once to arm the renewal and be taught the second call, then again with --handoff")
    s.add_argument("--handoff", metavar="NOTE", default=None,
                   help="what the next session of this seat must do, quoted — requires --renew; it REPLACES your seat memory (memory.md IS the handoff, owner ruling 2026-08-03: no body, no history) and is printed to your successor at its check-in. Target ~%d lines; longer warns, never refuses" % HANDOFF_MAX_LINES)
    s.add_argument("--handoff-file", dest="handoff_file", metavar="PATH", default=None,
                   help="the same note, read from a UTF-8 file instead of the command line — requires --renew, and never together with --handoff. Use it whenever the note has backticks, quotes or many lines, which a shell mangles before coord.py sees them")
    s.add_argument("--incomplete", metavar="REASON", default=None,
                   help="end this session UNFINISHED and say so, quoted — your done-contract is unmet and no successor is booted. It records disposition `incomplete` instead of `done`, so NO DAG EDGE ADVANCES and leader is routed the row carrying your reason. Use it instead of a plain checkout whenever your briefing asked for something that does not exist; never together with --renew, which says the opposite (the seat CONTINUES)")
    s.add_argument("--route", metavar="CHAIR", default=None, choices=list(STAFF_SEATS),
                   help="which STAFF CHAIR the session-closer mails this ending to. There is only "
                        "one: `leader`, the unblocker that holds this goal's authority. It is a "
                        "HINT, never an authority, and only the closer reads it")
    add_identity_flags(s)
    s.set_defaults(func=cmd_checkout)

    s = command(
        "send",
        "Send one typed message to an agent, a group, or everyone, and wake the recipients'\n"
        "panes. Send at coordination points: starting, before touching a shared surface, at a\n"
        "milestone, when blocked, when done. The log is the truth — wakes are best-effort.",
        "example:\n"
        "  coordinate send leader \"views build green; 12/12 pages render\" --type completion --inline\n"
        "next: coordinate pending — after an ask, it shows whether anyone settled it")
    s.add_argument("to", help="recipient: an agent name, a group name, 'all', 'owner' — or 'auto', which means THE SYSTEM PICKS (owner ruling D2): `auto` is the only address for --type stuck, and on --type ask it resolves to the leader (or straight to the owner if your seat.md says `human-interactive:`). Everything else is validated against the roster, the briefings and the groups, so a typo is refused")
    s.add_argument("message", nargs="?", help="the body, quoted — needs --inline when typed at a shell, because a shell eats backticks and $(...) before coord.py sees them. Anything with backticks, quotes or newlines goes through --file")
    s.add_argument("--type", required=True, choices=MESSAGE_TYPES,
                   help="completion (my briefing/milestone is done) | ask (I need an answer — send it to `auto` and the system routes it: the leader; from a `human-interactive:` seat, straight to the owner) | answer (replying to an ask) | verdict (a judge/checker ruling) | note (FYI) | stuck (I am BLOCKED and cannot proceed — address it to `auto` and the system routes it: it always reaches the leader, who escalates to the owner what it cannot solve. You never pick the recipient, and naming one is refused) | escalation (leader/judge only: a halt nobody in the run can clear — it wakes the owner) | queue-request (engine-internal: the pass-opener asking the daemon to seed the next wave — first body line is `queue-request: <milestone-id>/<verdict-id>/<pass-kind>`; the engine drains it, no seat is woken)")
    # W4 (adv, C42) — the two chat-routing sigils, promoted from body text to header mechanics.
    s.add_argument("--chat-thread", dest="chat_thread", metavar="ID",
                   help="route this row into a chat thread you already know: `<CHANNEL>:<ts>`, the plain `chat-thread:` line at the top of your prompt. Without it the row takes the owner's DM")
    s.add_argument("--deliver", choices=["post", "wake"], default=None,
                   help="what the named thread does with the row — post (verbatim, no agent, ~0.3s: a settled FACT) | wake (posted AND a sitting is minted to act on it). Needs --chat-thread; absent = mint a sitting and post nothing")
    s.add_argument("--milestone", metavar="ID",
                   help="`--type queue-request` ONLY: the milestone that became ready, written into the row's own `milestone:` header key. A verdict's milestone is stamped by `coordinate verdict` instead — the one door that can arm the escalation gate")
    s.add_argument("--approve-commit", dest="approve_commit", metavar="SHA",
                   help="`--type note` to `owner` ONLY: send this row as the plan's APPROVAL ASK, bound to this commit. It opens a thread in which the owner's `approve` STARTS EXECUTION, so it is refused unless your seat.md says `human-interactive:` AND the goal's `planning/approve-package.json` records this exact `bound_commit`. Without it a `to: owner` row is an ordinary question")
    s.add_argument("--re", dest="re_num", type=int, metavar="N",
                   help="the ask (or escalation) this settles — REQUIRED on --type answer, optional on verdict")
    s.add_argument("--supersedes", type=int, metavar="N",
                   help="retract message N: readers see the retraction inline wherever N is rendered")
    s.add_argument("--file", metavar="PATH",
                   help="read the body from a file ('-' = stdin) — shell-safe for backticks/quotes/newlines")
    s.add_argument("--inline", action="store_true",
                   help="accept the quoted positional body from a shell command line: you are asserting it has no backticks, $(...) or anything else a shell would have eaten before coord.py saw it (a proven substitution is refused even with this)")
    s.add_argument("--why", choices=sorted(BROADCAST_CLAUSES), metavar="CLAUSE",
                   help="REQUIRED on `send all`: which broadcast clause justifies it — "
                        + " | ".join(f"{k} ({v})" for k, v in sorted(BROADCAST_CLAUSES.items())))
    # B14 · ONE ACT — "a ruling recorded only in a message is not recorded". The append lands in
    # the goal's `decision-log` (`<goal>/decisions.md`) in this same invocation, AFTER the message
    # so the entry can cite its number; a failed append is LOUD and non-zero, never a silent skip.
    s.add_argument("--record", default="", metavar="TITLE",
                   help="record this message in the goal's decision-log (`<goal>/decisions.md`) in the SAME act: TITLE heads the appended entry, the body is this message, and the entry cites the message number it went out as")
    add_identity_flags(s)
    s.set_defaults(func=cmd_send)

    s = command(
        "verdict",
        "Record a milestone's trial verdict — THE ONLY VERB THAT ARMS THE ESCALATION GATE. It\n"
        "appends one `verdict` row whose why-clause is `milestone-<id>`, which is the exact\n"
        "string `escalate` and `fail-status` count; `send --why` cannot write it and is not\n"
        "widened to.\n"
        "\n"
        "THE VERB COMPOSES THE FIRST BODY LINE (`verdict: PASS` / `verdict: FAIL`) — you supply\n"
        "only the per-clause evidence beneath it. The count walks backwards from the newest row\n"
        "and stops at the first body with no verdict clause, so one hand-typed first line in the\n"
        "wrong shape would silently zero your own halt.\n"
        "\n"
        "RECORDING AND CHECKING THE BAR ARE ONE ACT: this always ends by running the escalation\n"
        "check, on PASS as well as FAIL, and prints its outcome. A PASS derives a count of 0, so\n"
        "nothing is appended. Re-running `escalate` afterwards is always safe and appends at most\n"
        "one row per milestone.\n"
        "\n"
        "--to IS THE PASS-OPENER, the seat that queues the next wave from this verdict (the\n"
        "unblock-checker seat of THIS goal — your seat prompt names it; it is not `owner`, which\n"
        "only the escalation row addresses, and it is not derivable, because the pass-opener is a\n"
        "loop back and taskforce.csv holds a DAG).",
        "example:\n"
        "  coordinate verdict m3 --fail --to plan-unblock-checker --file /tmp/verdict.txt\n"
        "next: coordinate fail-status m3 — the count, the resolved bar, and whether the "
        "escalation row is already in the log")
    s.add_argument("milestone",
                   help="the milestone id, bare (e.g. m3) — recorded as milestone-<id> in the row's why: clause, the string every escalation reader counts")
    s.add_argument("message", nargs="?",
                   help="the per-clause evidence body; the `verdict: PASS`/`verdict: FAIL` first line is composed for you and must NOT be typed here")
    g = s.add_mutually_exclusive_group(required=True)
    # `pass` is a Python keyword, hence the explicit dest. A required flag PAIR rather than a
    # second positional: `verdict FAIL m3` would transpose silently and record a verdict against
    # a milestone called FAIL.
    g.add_argument("--pass", dest="clause", action="store_const", const="PASS",
                   help="the milestone is ACCEPTED — composes `verdict: PASS`, which ends the FAIL run by construction")
    g.add_argument("--fail", dest="clause", action="store_const", const="FAIL",
                   help="the milestone FAILS — composes `verdict: FAIL` and extends the consecutive-FAIL run the bar is measured against")
    s.add_argument("--to", required=True, metavar="SEAT",
                   help="the PASS-OPENER seat that acts on this verdict (queues the gap wave, or enforces the halt) — your seat prompt names it; never `owner`, which only the escalation row addresses")
    s.add_argument("--file", metavar="PATH",
                   help="read the body from a file ('-' = stdin) — shell-safe for backticks/quotes/newlines")
    s.add_argument("--inline", action="store_true",
                   help="accept the quoted positional body from a shell command line: you are asserting it has no backticks, $(...) or anything else a shell would have eaten before coord.py saw it")
    add_identity_flags(s)
    s.set_defaults(func=cmd_verdict)

    s = command(
        "escalate",
        "The dod-judge retry escalation. Once a milestone's consecutive-FAIL count REACHES ITS\n"
        "BAR it appends EXACTLY ONE escalation row, addressed to the reserved `owner` token;\n"
        "otherwise it appends nothing and says why. The bar defaults to 2 and is per-goal\n"
        "configuration (`rbtv-goal retry-threshold`) — never type it, read it with\n"
        "`coordinate fail-status`. The count is DERIVED from the verdict log at the moment of\n"
        "the call (a PASS resets it by construction; never a stored counter), and derive +\n"
        "at-most-once scan + append share one lock hold — so the command is always safe to\n"
        "re-run.\n"
        "\n"
        "There is no recipient flag: one verb, one legal recipient. An initiation toward the\n"
        "human is addressed `owner` (d-agents-address-owner-not-master), and a seat that never\n"
        "types an address cannot type the wrong one.",
        "example:\n"
        "  coordinate escalate m3\n"
        "next: nothing to send — the row is in the log addressed to owner; the gap-wave loop\n"
        "      halts on it and waits for the owner's answer")
    s.add_argument("milestone",
                   help="the milestone id, bare (e.g. m3) — the log's verdict rows carry it as milestone-<id> in their why: clause")
    add_identity_flags(s)
    s.set_defaults(func=cmd_escalate)

    s = command(
        "fail-status",
        "What the escalation gate would decide for a milestone RIGHT NOW: its derived\n"
        "consecutive-FAIL count, the resolved bar and where that bar came from, whether the\n"
        "count has reached it, and whether the escalation row is already in the log. Writes\n"
        "nothing — not even a run-tag registration.\n"
        "\n"
        "It exists so the pass-opener stops re-deriving the authority for itself: the bar it\n"
        "reads here is the same object `escalate` enforces, so the two can never disagree.\n"
        "Queue nothing when at_bar or escalated is true; otherwise one gap-fill pass.",
        "example:\n"
        "  coordinate fail-status m3 --json\n"
        "next: nothing — this command reads state and changes none")
    s.add_argument("milestone",
                   help="the milestone id, bare (e.g. m3) — the same id `escalate` takes")
    s.add_argument("--json", action="store_true", help="machine-readable, for an asserting caller")
    s.set_defaults(func=cmd_fail_status)

    s = command(
        "queue-requests",
        "READ-ONLY: this goal's `queue-request` rows — the ENGINE's read path, and the reason no\n"
        "JavaScript ever parses `messages.md`. coord.py is the one bus parser; the daemon shells\n"
        "this verb the same way it shells `send`.\n"
        "\n"
        "Each row carries its idempotency key decomposed — `<milestone-id>/<verdict-id>/\n"
        "<pass-kind>`, read off the FIRST body line — plus TWO supersession facts: whether the\n"
        "request row itself was superseded, and whether the VERDICT it was minted from was. Both\n"
        "are filtered out by default; `--all` shows them. A row whose first body line is not the\n"
        "key is listed with a null key rather than dropped.\n"
        "\n"
        "It reports NO consumption state, because none is stored: a request is consumed when the\n"
        "pass's composed-name rows exist in `taskforce.csv`, which the create-only splice makes\n"
        "safe to re-check on every cadence.",
        "example:\n"
        "  coordinate --package /path/to/goal queue-requests --json\n"
        "next: nothing — this command reads state and changes none")
    s.add_argument("--json", action="store_true", help="machine-readable, for an asserting caller")
    s.add_argument("--all", action="store_true",
                   help="include superseded requests and requests whose verdict was superseded (the consumer skips both; this is for a human auditing the log)")
    s.set_defaults(func=cmd_queue_requests)

    s = command(
        "read",
        f"Show the messages you have not read yet, {READ_LIMIT} at a time. A plain read advances\n"
        "your persisted cursor through the last message SHOWN — nothing else. Every filter\n"
        "(--type/--addressed), plus --digest, --msg, --peek and --all, is peek-only and says so,\n"
        "so a filtered read can never drop the messages it hid from your inbox.",
        "example:\n"
        "  coordinate read\n"
        "next: read again while it reports more waiting; coordinate pending for the asks you owe")
    s.add_argument("--digest", action="store_true", help="one line per message instead of full bodies (no cursor move)")
    s.add_argument("--msg", type=int, default=None, metavar="N", help="show message N alone, in full, with its ask link (no cursor move)")
    s.add_argument("--after", type=int, default=None, metavar="N",
                   help="override the stored cursor: show messages after N (recovery after a context loss)")
    s.add_argument("--limit", type=int, default=None, metavar="N", help=f"messages per batch (default {READ_LIMIT}; 0 = no limit)")
    s.add_argument("--peek", action="store_true", help="show without advancing the cursor")
    s.add_argument("--all", action="store_true", help="replay the whole log without advancing the cursor")
    s.add_argument("--type", choices=MESSAGE_TYPES, default=None, help="show only this message type (no cursor move)")
    s.add_argument("--addressed", choices=["any", "direct", "broadcast"], default="any",
                   help="any = to me, my groups, or everyone (default) | direct = only messages naming me | broadcast = only messages to all")
    add_pretty_flag(s)
    add_identity_flags(s)
    s.set_defaults(func=cmd_read)

    s = command(
        "status",
        "One-shot orientation — run it after a relaunch, a context loss, or whenever you are\n"
        "unsure where you stand: who you are, whether your pane can still be woken, owner\n"
        "presence, your cursor against the log tail, unread by type, and the asks waiting on you.\n"
        "The pane check needs a live tmux server; without one every pane honestly reads ok.",
        "example:\n"
        "  coordinate status\n"
        "next: whatever its own `next:` line says — read, pending, or back to your task")
    add_pretty_flag(s)
    add_identity_flags(s)
    s.set_defaults(func=cmd_status)

    s = command(
        "pending",
        "The open asks, derived over the WHOLE log and not from your cursor: what is waiting on\n"
        "you, what is open to everyone, and which of your own asks nobody has answered. An ask\n"
        "stays open until an answer or verdict --re's it, or it is superseded.",
        "example:\n"
        "  coordinate pending\n"
        "next: coordinate send <asker> \"<answer>\" --type answer --inline --re <ask#>")
    add_pretty_flag(s)
    add_identity_flags(s)
    s.set_defaults(func=cmd_pending)

    s = command(
        "workers",
        "The roster: one CURRENT row per agent — alive, dead pane, or checked out; what each is\n"
        "working on; and how many messages each one has still to read (lag=, the same exact\n"
        "unread count that seat's own `status` reports). ACTIVE rows are verified against live\n"
        "tmux panes, so a seat whose pane is gone shows DEAD?.",
        "example:\n"
        "  coordinate workers\n"
        "next: supervise close-seat <agent> for a DEAD? row; send to reach a live one")
    s.add_argument("--full", action="store_true", help="do not truncate the 'working on' summaries")
    s.add_argument("--history", action="store_true", help="every historical row, not just each agent's current one")
    add_pretty_flag(s)
    s.set_defaults(func=cmd_workers)

    s = command(
        "owner",
        "Record whether the owner is at the keyboard. Workers were inferring it and getting it\n"
        "wrong (P15), so it is stated instead. Leader's to set — or the owner's own, from a\n"
        "shell outside any seat.",
        "⚠ NARROWING (task 7.85): `afk` used to carry the door-closed case too, because it was the\n"
        "least-wrong of two values. It no longer does — that case is `reachable`. `present` and\n"
        "`afk` mean exactly what they always meant; what changed is that neither has to stretch.\n"
        "example:\n"
        "  coordinate owner afk --note \"back in 2h\"\n"
        "  coordinate owner reachable        # at the PC, no door running — no note needed\n"
        "next: nothing to send — coordinate status and workers report it from the surface\n"
        "      this command just wrote; a hand-typed copy is a second answer that can disagree")
    # ⚠ choices AND help are DERIVED from OWNER_STATES — never re-spelled here. A hand-written
    # `choices=[...]` beside a hand-written help string is two more places for the state set to
    # drift from what the consumers actually render.
    s.add_argument("state", choices=list(OWNER_STATES),
                   help="; ".join(f"{k} = {v[0]}" for k, v in OWNER_STATES.items()))
    s.add_argument("--note", default="", help="optional context, e.g. 'back in 2h'")
    add_identity_flags(s)
    s.set_defaults(func=cmd_owner)

    s = command(
        "session-open",
        "Open a seat's session-trace row — the row `sessions.csv` gets when the kit launches a\n"
        "seat, exposed as a verb for a launcher that is NOT this file's own `launch`. The daemon's\n"
        "spawn path is that launcher: without this, a daemon-launched package has no trace at all,\n"
        "so nothing that reads sessions.csv can say how any of its seats ended.\n"
        "\n"
        "CALL IT ONLY AFTER THE SEAT IS VERIFIED UP — a row for a seat that never booted is the\n"
        "lie the trace exists to prevent, and this command cannot check that for you. Refused for\n"
        "a seat this package has no descriptor for; a no-op (exit 0) when the seat already has an\n"
        "open row, so a retrying launcher cannot double-write.",
        "example:\n"
        "  supervise --package /abs/run-3 session-open builder\n"
        "next: coordinate workers — the seat must still CHECK IN; the trace row is not a check-in")
    s.add_argument("seat", help="the TARGET seat whose session row is opened, as in its descriptor's `agent:` key — never the caller")
    s.add_argument("--pane", default=None,
                   help="the seat's tmux pane id, whose pid/starttime/tty become the row's identity pair (the pane's, never this process's). Omit it off tmux: the identity cells stay blank, which is honest — a fabricated one authenticates an impostor")
    s.add_argument("--wait", type=float, default=None,
                   help="seconds to wait for a claude seat's transcript before recording its native-session-id UNRESOLVED (default: the module's own budget). 0 records it unresolved immediately — checkin backfills it either way")
    s.set_defaults(func=launch.cmd_session_open)

    s = command(
        "launch",
        "(leader) Open one tmux seat per worker briefing and start its harness. Harness, model,\n"
        "effort, cwd and pane-vs-window all come from each briefing's frontmatter, so leader\n"
        "launches without reading any briefing. A bare launch never boots leader itself.\n"
        "Before any codex/opencode seat opens, its launch root's worker mirror (AGENTS.md +\n"
        ".agents/) is refreshed once, so the seat reads current rules and not whatever the\n"
        "last installer run left behind. A failed refresh warns and launches anyway.\n"
        "LANE-AWARE (E22): on a goal whose `execution-lane` marker reads `daemon`, every door\n"
        "of this command (a bare launch, --only, --declare-only, --rerun, --reopen) ENQUEUES a\n"
        "caged headless sitting through the daemon's own spawn door instead of opening a tmux\n"
        "pane — the daemon composes the cage and the boot prompt at dispatch and opens the\n"
        "seat's sessions.csv row; a dedup/brake refusal from that door is reported as a refusal.\n"
        "Admission is identical on both lanes; --tmux-target is refused on the daemon lane.",
        "example:\n"
        "  supervise launch --only judge-ux,judge-parity\n"
        "next: coordinate workers — every seat must check in; one that does not never booted")
    s.add_argument("--only", help="comma-separated agent names to launch (stages: e.g. --only judge-ux,judge-parity)")
    s.add_argument("--dry-run", action="store_true", help="print the command each seat would start with, open nothing")
    # 7.362 (F18): NOT an override and NOT a member of the --force family — it overrides no gate
    # and admits no seat. It SUPPLIES the input the environment refusal already demands, for the
    # one caller that cannot carry it any other way: a daemon-fired exec inherits no tmux
    # environment (`runToolLikeExec` passes `envFile: null`). Absent or empty it changes nothing.
    s.add_argument("--tmux-target", dest="tmux_target", metavar="ID", default="",
                   help="the tmux pane or window id the new seats are opened relative to, named "
                        "EXPLICITLY instead of inherited from $COORD_LAUNCH_TARGET/$TMUX_PANE. "
                        "For a daemon-fired exec, which has neither. NOT an override: empty or "
                        "absent falls through to those two variables and to the same refusal — "
                        "an empty target is never defaulted, because tmux resolves one to the "
                        "MOST RECENT session, which is how a stray launch reaches the live room. "
                        "REFUSED on a goal whose execution-lane is `daemon` (E22): that lane opens "
                        "no pane, and a flag silently ignored is a flag that lies")
    s.add_argument("--force-memory", action="store_true",
                   help="override the MEMORY gate only (--force is a separate flag, for this "
                        "command's other refusals)")
    # 7.251 (C1.2): NOT an override and NOT a member of the --force family. It admits ONE named
    # seat whose last session ENDED UNDECLARED, for a session that declares its own ending and
    # does nothing else. Its VALUE is the written trail, so the instrument cannot be invoked
    # without one — presence declares the purpose, the value carries the anchor.
    s.add_argument("--declare-only", metavar="LEADER-ANCHOR", default=None,
                   help="admit ONE --only seat whose last session ended UNDECLARED, so that the "
                        "session it opens can DECLARE THAT ENDING and check out. ⚠ F-3, corrected "
                        "D42: 'it does no work' was the caller's stated PURPOSE, enforced by "
                        "nothing — this flag plumbs nothing into the pane and the session it "
                        "opens is an ordinary one. What the flag actually decides is ADMISSION: "
                        "it admits the UNDECLARED class and nothing else. It is NOT the way to "
                        "bring a CRASHED seat back to work — a `failed`/`crash` ending's door is --rerun "
                        "(D42). Takes the leader's investigation/acceptance anchor for that seat, "
                        "which is recorded as the trail. NOT an override: the target stays "
                        "UNDECLARED until its new session supersedes it, a seat with a DECLARED "
                        "ending is still refused, and --force/--force-memory are untouched and "
                        "carry no part of this")
    # D42 (2026-08-20): NOT an override and NOT a member of the --force family. A FOURTH
    # independent parameter. It admits ONE named seat whose current ENDING is `failed` with a
    # crash-shaped reason class — a harness that DIED with the work unknown — for an ORDINARY
    # WORKING SESSION. Its VALUE is the written trail, so the instrument cannot be invoked
    # without one.
    #
    # ⚠ THE FROM-STATE WAS RE-SPELLED, NOT WIDENED [T1-R3, T4-R7, spec-supervisor §3/§4]. It read
    # `exited` written by the kit until the redesign retired that word: `exited` was a fifth ending
    # vocabulary carrying NO reason at all, so nothing downstream could classify it. The same fact
    # is now `failed` + a mandatory reason class, stamped by the SUPERVISOR from evidence, and the
    # ending store refuses the old word at the write boundary. `failed` with any other class
    # (`outputs-missing`) is still refused by this door and routed by name.
    s.add_argument("--rerun", metavar="LEADER-ANCHOR", default=None,
                   help="RE-RUN ONE --only seat whose current ending is `failed` with reason "
                        "class `crash` or `provider-error` (the supervisor's stamp from evidence: "
                        "the harness died, the work is UNKNOWN — never finished). "
                        "The seat boots on its ordinary boot prompt and DOES ITS JOB; this is a "
                        "real working session, not a declaration. Takes the leader's "
                        "investigation anchor for that seat, which is recorded as the trail. The "
                        "`failed` ending is NOT rewritten, cleared or relabelled — it stays on the "
                        "record and is superseded when the new session writes its own ended row, "
                        "so no `rule-disposition` is needed first. NOT an override: any other "
                        "from-state is still refused, and --force/--force-memory are untouched "
                        "and carry no part of this")
    # D54/D66/D72 (owner, 2026-08-22): NOT an override and NOT a member of the --force family. A
    # FIFTH independent parameter, beside `--rerun`. It admits ONE named seat whose last ENDED row
    # carries `done` — a leader-written or seat-written FINISHED ending — for an ORDINARY WORKING
    # SESSION on a LATE FINDING. Its VALUE is the recorded reason, written DURABLY on the new row
    # (unlike `--rerun`'s console-only trail), so the instrument cannot be invoked without one.
    s.add_argument("--reopen", metavar="REASON", default=None,
                   help="RE-OPEN ONE --only seat whose last session ENDED `done` (a FINISHED "
                        "ending), on a LATE FINDING against that finished work (D54). The seat "
                        "boots on its ordinary boot prompt and DOES ITS JOB; this is a real "
                        "working session, not a ruling. Takes the leader's reason for the "
                        "reopen, which is RECORDED on the new session's `reopen-reason` column "
                        "(D72) — unlike `--rerun`'s anchor, this is not console-only. Bounded to "
                        "at most 2 reopens of the same seat citing the SAME reason (D66). Any "
                        "seat that already ran depending on this seat's retracted `done` is "
                        "flagged (D72's walk-forward), never rolled back. The `done` row is NOT "
                        "rewritten, cleared or relabelled — it stays on the record and is "
                        "superseded when the new session writes its own ended row. NOT an "
                        "override: any other from-state is still refused (that is `--rerun`'s "
                        "door for a `failed`/`crash` ending; `supervise instruct <seat> <kind>` "
                        "is the leader's ruling instrument for the rest — the deleted "
                        "`rule-disposition` [T2-R12, T1-R9] is NOT what replaced it), and "
                        "--force/--force-memory are "
                        "untouched and carry no part of this")
    add_identity_flags(s)
    s.set_defaults(func=launch.cmd_launch)

    s = command(
        "surface-refusal",
        "(daemon) land ONE cage-admission seed refusal on this goal's bus, addressed `owner` —\n"
        "IDEMPOTENT per (seat, reason). The daemon's seed pass repeats every cadence, and this\n"
        "verb is what keeps a standing refusal from appending one row per tick: the dedup marker\n"
        "is the body's first line (`seed-refusal: <seat> <sha256[:12] of reason>`), and the scan\n"
        "and the append share one lock hold.",
        "example:\n"
        "  supervise --as ignite-daemon surface-refusal audio-component-smith --reason \"...\" --json\n"
        "next: nothing by hand — the daemon's seeding pass calls this; read the row with "
        "coordinate read — the cage envelope is fixed at plan time now, so a refusal here is a "
        "planning fix, not a runtime widen")
    s.add_argument("seat", help="the refused seat — the row is ABOUT it, never FROM it")
    s.add_argument("--reason", metavar="TEXT", default=None,
                   help="the refusal text, verbatim from the admission gate — the dedup key is derived from it")
    s.add_argument("--json", action="store_true",
                   help="machine-readable result on stdout — the shape the daemon's seeding pass reads")
    add_identity_flags(s)
    s.set_defaults(func=ready.cmd_surface_refusal)

    s = command(
        "renewal-state",
        "(engine) ONE seat's renewal answer, verbatim from `renewal_state` — the one reader of\n"
        "the successor-pending signal (LE-10). READ-ONLY: registers nothing, writes nothing,\n"
        "messages nobody. `successor-pending` means a `--renew` hand-over is in flight (or the\n"
        "successor was already placed) and the seat is NOT dead; `no-successor` means nothing is\n"
        "coming and the seat's records mean what they say.",
        "example:\n"
        "  supervise --package <goal-folder> renewal-state <seat> --json\n"
        "next: nothing by hand — the engine's exit decision consumes this; a human reads the "
        "same fact in `status`'s lifecycle block")
    s.add_argument("seat", help="the seat whose renewal is being asked about")
    s.add_argument("--json", action="store_true",
                   help='{"seat", "state", "why"} — `state` is `successor-pending` or `no-successor`')
    s.set_defaults(func=ready.cmd_renewal_state)

    # ── W3 · the leader's actuator ─────────────────────────────────────────────────────────────
    # `widen-cage` (the leader's audited permission edit) was DELETED here (ruling [T2-R6, C-6],
    # 2026-08-24): runtime auto-widen is dead, the seat's cage envelope is fixed at plan time.
    s = command(
        "route-fail",
        "Route a FAIL back to a receiver that EXISTS. The route is your own seat.md declaration\n"
        "(`on-fail-relaunch:`); an UNDECLARED fail goes to the `leader`, because a verdict with no\n"
        "declared receiver is exactly the case that was lost silently.\n"
        "\n"
        "A declared target is checked for EXISTENCE (a well-formed name that names no seat is how a\n"
        "routed FAIL reached nobody) and for a bindable ENDED SESSION, then handed a PAYLOAD FILE\n"
        "that its next boot prompt folds in. D12 · THIS VERB GRANTS NOTHING — the goal watcher\n"
        "(`supervisor/reconcile.js`) is what relaunches a seat whose last ended row is NON-TERMINAL and\n"
        "who has unread mail; a bare payload with no non-terminal row would strand the seat on its\n"
        "STALE SEED with nothing to bring it back.",
        "example:\n"
        "  supervise route-fail \"the contract in step 3 contradicts step 1\" --go\n"
        "next: coordinate read — the routed seat relaunches on the next seeding pass")
    s.add_argument("message", nargs="?",
                   help="the fail, quoted. Anything with "
                        "backticks, quotes or newlines goes through --file")
    s.add_argument("--file", metavar="PATH", help="read the body from a file instead")
    s.add_argument("--go", action="store_true", help="act (bare = report, write nothing)")
    add_identity_flags(s)
    s.set_defaults(func=attest.cmd_route_fail)

    # ── B9/B10 · THE LEADER'S RULING ACTS ──────────────────────────────────────────────────────
    # `rule-disposition` (the deleted verb these replace) is NOT resurrected and neither is its
    # word: `disposition` is a KILLED WORD at the ending store's own door
    # (`state-store/vocabulary.js`). The bodies are `ruling.py`'s; see its header for why there is
    # no per-verb role gate (there is none anywhere in this kit [T2-R10, D24, F-simplicity-7]) and
    # why the audience bound is THIS TUPLE — both verbs sit on `supervise` only, so `coordinate
    # accept` is refused by name at the parser.
    s = command(
        "accept",
        "ACCEPT a seat's finished work — its current ending becomes `done` in ONE act, and every\n"
        "`after` edge waiting on that seat advances.\n"
        "\n"
        "THE OUTPUTS ARE RE-CHECKED, NOT TAKEN ON YOUR WORD: the seat's declared `## Outputs` are\n"
        "graded by the same mechanical check the store runs, and an acceptance of work whose\n"
        "outputs are not on disk is REFUSED here by name rather than silently downgraded.\n"
        "\n"
        "`--anchor` is mandatory and is RECORDED, NEVER VERIFIED — no tool can check that an anchor\n"
        "names a real investigation, and a `done` citing nothing is a `done` nobody can audit.",
        "example:\n"
        "  supervise accept builder --anchor 'messages.md #142 — outputs md5-checked' --go\n"
        "next: supervise ready-seats — the successors this acceptance just unblocked")
    s.add_argument("seat", help="the TARGET seat whose finished work you are accepting (never your own name)")
    s.add_argument("--anchor", default="", metavar="REF",
                   help="WHY it is accepted — the message ref, decision anchor or evidence you read (recorded, never verified)")
    s.add_argument("--go", action="store_true", help="act (bare = report what would change, write nothing)")
    # No `--force`: neither refusal this verb raises HAS an override. A missing `--anchor`, a
    # seat this goal does not staff, an instruction kind the daemon cannot execute and a declared
    # output that is not on disk are all facts, not policies — offering a flag whose own help says
    # it "overrides this command's refusal" would promise a door that is not there.
    add_identity_flags(s, force=False)
    s.set_defaults(func=cmd_accept)

    s = command(
        "instruct",
        "RULE on a seat's ended session, so it stops re-waking the chair. The judgment is recorded\n"
        "where the daemon ALREADY drains it — `.rbtv/runtime/ignite/leader-instructions/` — and is\n"
        "applied once, at the top of the next reconcile pass, then filed under `done/`.\n"
        "\n"
        "The kind is one of a CLOSED list of four, read off `supervisor/relaunch-budget.js` rather\n"
        "than spelled here: `rewrite-brief` (--brief-file + --brief-path: new words, lane re-armed\n"
        "for one authorized relaunch) · `reassign` (--to-seat: another seat design takes the work)\n"
        "· `blocked-pending-plan-gap` (--gap [--milestone]: the gap is in the PLAN, and a scoped\n"
        "re-plan request is recorded) · `escalate` (--report-file: a formed decision-ask to the\n"
        "owner). A fifth would be a remedy verb nobody ruled [D6, T4-R6].\n"
        "\n"
        "THE WALL [CF-3, T2-R5]: an instruction may carry a JUDGMENT, never the seat's work. Text\n"
        "rides a FILE and never argv — a shell eats backticks and $(...) before this command sees\n"
        "them.\n"
        "\n"
        "This is NOT the deleted `rule-disposition` and it does not write that verb's surface: the\n"
        "grant-store authority model went with it [T2-R12, T1-R9] and `disposition` is a killed\n"
        "word at the ending store's door. What is recorded here is a leader INSTRUCTION, and the\n"
        "daemon is what stamps the resulting ending.",
        "example:\n"
        "  supervise instruct builder reassign --to-seat builder-b --go\n"
        "next: supervise ready-seats — the lane the daemon re-armed on your instruction")
    s.add_argument("seat", help="the TARGET seat whose ended session you are ruling on")
    s.add_argument("kind", help="the instruction: rewrite-brief | reassign | blocked-pending-plan-gap | escalate")
    s.add_argument("--brief-file", metavar="PATH", help="rewrite-brief: the file holding the new brief text")
    s.add_argument("--brief-path", metavar="PATH", help="rewrite-brief: where that brief lands on disk")
    s.add_argument("--to-seat", metavar="NAME", help="reassign: the seat design that takes the work")
    s.add_argument("--gap", default="", metavar="TEXT", help="blocked-pending-plan-gap: what the plan does not say")
    s.add_argument("--milestone", default="", metavar="ID", help="blocked-pending-plan-gap: the milestone the gap sits under")
    s.add_argument("--report-file", metavar="PATH", help="escalate: the file holding the decision-ask the owner reads")
    s.add_argument("--go", action="store_true", help="act (bare = report the payload, write nothing)")
    # No `--force`: neither refusal this verb raises HAS an override. A missing `--anchor`, a
    # seat this goal does not staff, an instruction kind the daemon cannot execute and a declared
    # output that is not on disk are all facts, not policies — offering a flag whose own help says
    # it "overrides this command's refusal" would promise a door that is not there.
    add_identity_flags(s, force=False)
    s.set_defaults(func=cmd_instruct)

    s = command(
        "export-transcript",
        "Capture a seat's full pane scrollback into workers/<agent>/transcripts/. checkout and\n"
        "depart already do this for you — run it by hand for a mid-run milestone, or for a seat\n"
        "you are about to close.",
        "example:\n"
        "  coordinate export-transcript builder --label milestone2\n"
        "next: supervise close-seat builder — once the memory.md this seat owes is written")
    s.add_argument("target", help="the TARGET seat whose pane is captured (the seat acted on, not the caller)")
    s.add_argument("--label", default="", help="optional filename suffix, e.g. 'milestone2'")
    s.set_defaults(func=cmd_export_transcript)

    s = command(
        "close-seat",
        "Export the target seat's transcript, check its row out, kill its pane — and with\n"
        "--renew relaunch it fresh. Only the daemon or leader runs this, directly, on a seat\n"
        "that is finished, near its context limit, or a dead pane needing cleanup.",
        "example:\n"
        "  supervise close-seat builder --renew\n"
        "next: coordinate workers — confirm the seat is gone (or back, with --renew)")
    s.add_argument("target", help="the TARGET seat being closed (the seat acted on, never the caller's own name)")
    s.add_argument("--renew", action="store_true", help="relaunch the seat fresh after killing it")
    s.add_argument("--no-export", action="store_true", help="skip the transcript export (e.g. pane already dead)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_close_seat)

    s = command(
        "execution",
        "Print this goal's current DATED EXECUTION STAMP (YYYY-MM-DDx) — the delimiter that\n"
        "separates this boot's rows from previous boots' in the goal's single, append-only\n"
        "files (design-lock item 5). --mint starts a NEW execution; it is the BOOT's act and\n"
        "belongs to whoever creates the room, never to a seat.",
        "example:\n"
        "  coordinate execution\n"
        "next: nothing — this is a read")
    s.add_argument("--mint", action="store_true",
                   help="mint the NEXT stamp (boot only — the room-creating act)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_execution)

    s = command(
        "finish-goal",
        "THE FINISH EDGE (7.607 E1) — the ONE thing that finishes a goal and the ONE thing that\n"
        "stops its watchers. Records an append-only finish EVENT in the coordination log, then\n"
        "tears the room down. Until it fires, an absent room is a CRASH and the watcher relaunches\n"
        "it; nothing else — no closed row, no empty room, no dead seat — finishes a goal.\n"
        "THE LEADER'S ACT: where the goal's taskforce.csv names a `leader` row, only that seat may\n"
        "fire it — every other identity is refused, naming the leader. The event is attributed to\n"
        "the RESOLVED caller, so run it as yourself and never on another seat's behalf.",
        "example:\n"
        "  coordinate finish-goal --note 'milestones all accepted'\n"
        "next: nothing. The goal is over; the watchers exit on their next pass")
    s.add_argument("--note", default="", help="free text appended to the finish event's body")
    add_identity_flags(s)
    s.set_defaults(func=cmd_finish_goal)

    s = command(
        "advance-state",
        "Stamp ONE row on the goal's state cursor (state.csv) — the append-only record of WHERE\n"
        "the goal stands. One row per ADVANCE, never per turn, per message or per commit; the\n"
        "latest row is the position. `session-id` is RESOLVED from your own open session row, so\n"
        "the stamp records the session that made it and not one you typed. Rows are never edited\n"
        "or deleted: a wrong row is corrected by a NEW row whose --note names the one it\n"
        "supersedes. Position only — narrative belongs in a message, rulings in decisions.md.",
        "example:\n"
        "  coordinate advance-state verifying --note 'm4 spine complete; handed to the verifier'\n"
        "next: coordinate send — the cursor says WHERE the goal is; it never says why")
    s.add_argument("state", choices=GOAL_WORKING_STATES,
                   help="the goal's working-lifecycle state at this advance — the KG `goal state` "
                        "vocabulary, and nothing else is accepted")
    s.add_argument("--note", default="",
                   help="one line of position context, quoted — e.g. which row this one "
                        "supersedes. NOT a log entry: narrative goes to a message")
    add_identity_flags(s)
    s.set_defaults(func=cmd_advance_state)

    s = command(
        "reap",
        "One sweep over the awaiting-close debt: seats that finished their own lifecycle whose\n"
        "panes the leader has not yet freed. OBSERVES BY DEFAULT — a bare `reap` reports the debt\n"
        "and records this pass; --go is what kills. A pane is freed only when it is at least\n"
        f"{REAP_MIN_AGE_MIN}min old, its transcript exists, the pane still holds exactly the\n"
        "harness processes it checked out with (so no human has picked it up), and the condition\n"
        "has held across TWO passes at least "
        f"{REAP_MIN_PASS_GAP_MIN}min apart — one reading is a snapshot, two is a trend.\n"
        "Reaping frees the PANE only; each seat still owes a close-seat afterwards.",
        "example:\n"
        "  supervise reap            # observe and confirm, kill nothing\n"
        "  supervise reap --go       # free the panes already confirmed READY\n"
        "next: coordinate workers — the debt is listed there until close-seat settles it")
    s.add_argument("--go", action="store_true",
                   help="actually free the confirmed panes (without it, reap only observes)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_reap)

    s = command(
        "kill-pane",
        "Reap ONE pane by id directly (task 7.91) -- the route to a leaked pane when a raw\n"
        "`tmux kill-pane` is refused by the harness auto-mode classifier and `close-seat` needs a\n"
        "roster-known SEAT NAME rather than a bare pane id. Kills the PANE ONLY, like `reap` --\n"
        "no transcript export, no roster mutation; the seat still owes a close-seat afterwards.\n"
        "Refuses UNCONDITIONALLY (no --force) if the pane is not on this run's CURRENT roster, or\n"
        "belongs to a seat carrying `relays:` (a human-contact door). Refuses, escapable with\n"
        "--force, if the pane's row is still roster-ACTIVE (not roster-done).",
        "example:\n"
        "  supervise kill-pane %482\n"
        "next: coordinate workers -- confirm the pane is gone; the seat still owes a close-seat")
    # dest is `pane_id`, NEVER `pane` -- `args.pane` is reserved: resolve_agent()/detect_pane()
    # read it as an override for the CALLING pane (the same attribute `checkin --pane` sets), so a
    # positional named `pane` here would make the TARGET silently stand in for the caller during
    # identity resolution -- caught by this row's own selftest (a door/active refusal that only
    # "worked" with --force, because --force is what let resolve_agent's OWN identity-mismatch
    # refusal through, not because the door/active logic below it was ever reached).
    s.add_argument("pane_id", metavar="pane",
                    help="the tmux PANE ID to kill (e.g. %%482) -- never a seat name")
    add_identity_flags(s)
    s.set_defaults(func=cmd_kill_pane)

    s = command(
        "terminate-pid",
        "(leader) Terminate ONE process named by pid, with the authorization written to the\n"
        "coordination log (task 7.153, G-303). The verb the leader was always authorized to have\n"
        "and never had: a detached non-seat process — a stray watch.py, a loop a seat could not\n"
        "stop — could only be ended by a hand `kill`, which nothing replays and nothing audits.\n"
        "`kill-pane` cannot serve it: a detached process has no pane.\n"
        "NON-SEAT RADIUS BY CONTRACT: a pid at or below ANY current roster row's pane is REFUSED,\n"
        "and no --force lifts it — a seat ends through close-seat/reap/kill-pane, which do the\n"
        "roster, transcript and trace work this verb deliberately does not.\n"
        "Sends the ONE signal it was asked for and then VERIFIES from /proc; a SIGTERM that does\n"
        "not take is reported and exits non-zero, never silently escalated to SIGKILL.",
        "example:\n"
        "  supervise terminate-pid 1302382 --reason \"stray watch.py loop, G-303 case 2\"\n"
        "  supervise terminate-pid 1302382 --starttime 884118 --reason \"...\"   # pid-reuse guard\n"
        "next: coordinate read -- the authorization and its outcome are on the log for the audit")
    s.add_argument("pid", type=int,
                   help="the pid to terminate -- NAMED, never inherited: there is no 'current "
                        "process' default and never will be. Re-measure it at the instant of use "
                        "(`ps -eo pid=,args=`); a pid carried from an earlier reading names a "
                        "stranger as often as a corpse")
    s.add_argument("--reason", required=True,
                   help="why this process is being terminated, quoted -- it is written into the "
                        "authorization record, which is the whole point of the verb: a terminate "
                        "nobody can later ask 'why' about is the hand kill this replaces")
    s.add_argument("--starttime", default=None, metavar="S",
                   help="the target's /proc starttime as YOU measured it -- a pid ALONE is not an "
                        "identity, and the gap between your reading and this call is exactly the "
                        "window a recycled pid slips through. Supplying it turns a stale pid into "
                        "a refusal instead of a stranger's death")
    s.add_argument("--signal", choices=("TERM", "KILL"), default="TERM",
                   help="which signal to send (default TERM). KILL is a SECOND, deliberate act "
                        "after a TERM was seen not to take -- never this command's silent second "
                        "half")
    add_identity_flags(s)
    s.set_defaults(func=cmd_terminate_pid)

    s = command(
        "relaunch-pane",
        # No role parenthetical anymore [T2-R10, D24, F-simplicity-7] — this command is callable
        # by any resolved identity. The prose below still names the chief-of-staff, and correctly:
        # that clause is about the stopgap this command RETIRED, not about who may call it.
        "Relaunch a seat's harness INTO a named,"
        " already-registered pane,\n"
        "in place (task 7.95, G-282) -- the door's own path back up when a plain `launch`\n"
        "would move it and `close-seat --renew` is refused by the relays: guard.\n"
        "Never kills anything: refuses unless the pane is already bare (no harness running) and\n"
        "the roster row is already roster-done. Never routes through close-seat and never needs\n"
        "--force for the intended case -- retires the chief-of-staff's raw `tmux send-keys`\n"
        "stopgap, restoring the memory floor, check_bindings (G-51), and the roster/session-\n"
        "trace writes that stopgap skipped.",
        "example:\n"
        "  supervise relaunch-pane owner-liaison %501\n"
        "next: coordinate workers -- confirm the seat checked back in on the SAME pane")
    s.add_argument("target", help="the TARGET seat to relaunch (the seat acted on)")
    s.add_argument("pane_id", metavar="pane",
                    help="the tmux PANE ID to relaunch into (e.g. %%501) -- must match the "
                         "roster's own recorded pane for TARGET; resolve it fresh from "
                         "`coordinate workers`, never from memory (bars.md 3)")
    s.add_argument("--dry-run", action="store_true",
                    help="print the command that would start, respawn/launch nothing")
    s.add_argument("--force-memory", action="store_true",
                    help="override the MEMORY gate only (--force is a separate flag, for the "
                         "roster-still-active refusal)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_relaunch_pane)

    s = command(
        "approve",
        "Answer a seat's interactive permission prompt by sending keys to its\n"
        "registered pane, then echo the pane tail so you can verify what happened. Inspect the\n"
        "pane and DECIDE first — this only presses the button.",
        "example:\n"
        "  supervise approve builder --keys 2\n"
        "next: run it again if the echoed tail still shows the prompt")
    s.add_argument("target", help="the TARGET seat whose pane is showing the prompt (the seat acted on)")
    s.add_argument("--keys", default="", help="literal keys before Enter (e.g. 1, 2, 3, n); empty = Enter only")
    s.add_argument("--no-enter", action="store_true", help="send keys without a trailing Enter")
    s.set_defaults(func=cmd_approve)

    s = command(
        "panel",
        "(leader) Split a short full-width overview strip into THIS window: the live session\n"
        "overview (windows, panes, seat names) plus plan usage. Idempotent — it skips if an\n"
        "overview pane is already open.",
        "example:\n"
        "  coordinate panel\n"
        "next: supervise launch — the strip tracks the seats it opens")
    add_identity_flags(s)
    s.set_defaults(func=cmd_panel)

    s = command(
        "depart",
        "Self-service exit for an ephemeral seat: export your own transcript, check out, and kill\n"
        "your own pane, in one command. It takes no name — a seat can only depart ITSELF; leader\n"
        "removes other seats with close-seat.",
        "example:\n"
        "  coordinate depart\n"
        "next: nothing — your pane is gone and your row reads checked out")
    add_identity_flags(s)
    s.set_defaults(func=cmd_depart)

    s = command(
        "create-group",
        "Open a message group for ONE workstream or overlap, so its thread leaves the `all`\n"
        "channel. You and leader are always members. This is what the startup round produces:\n"
        "one group per identified overlap, and detailed discussion happens there.",
        "example:\n"
        "  coordinate create-group views-render builder judge-ux\n"
        "next: coordinate send views-render \"<why this group exists>\" --type note --inline")
    s.add_argument("group", help="the group name — a workstream, never an agent name or 'all'")
    s.add_argument("members", nargs="*", help="agent names to include (you and leader are added automatically)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_create_group)

    s = command(
        "add-to-group",
        "(leader) Add members to an existing group — the way a late seat joins a thread that is\n"
        "already running.",
        "example:\n"
        "  coordinate add-to-group views-render toolsmith\n"
        "next: coordinate send views-render \"<who joined, and why>\" --type note --inline")
    s.add_argument("group", help="an existing group name")
    s.add_argument("members", nargs="+", help="agent names to add")
    add_identity_flags(s)
    s.set_defaults(func=cmd_add_to_group)

    s = command(
        "remove-from-group",
        "(leader) Remove members from an existing group — the only sanctioned way to undo a\n"
        "membership, since coordination/ is script-managed and hand-editing it is banned. Use it\n"
        "when a seat's lane is done, or when a special-case seat (watcher, engineer, a closer)\n"
        "was added before the G-32 rule that now refuses it.",
        "example:\n"
        "  coordinate remove-from-group ceremony watcher\n"
        "next: coordinate send ceremony \"<who left, and why>\" --type note --inline")
    s.add_argument("group", help="an existing group name")
    s.add_argument("members", nargs="+", help="agent names to drop (all must currently be members, unless --force)")
    add_identity_flags(s)
    s.set_defaults(func=cmd_remove_from_group)

    s = command(
        "descriptors",
        "Read-only structural audit of every seat descriptor against taskforce.csv: name vs\n"
        "folder, cwd, orphans both directions, duplicate names, binding divergence. Opens no\n"
        "briefing body — fields and paths only — so no seat's instructions reach the caller.",
        "example:\n"
        "  supervise descriptors\n"
        "next: nothing — findings are reported to whoever owns seats/, never fixed here")
    s.set_defaults(func=launch.cmd_descriptors)

    s = command(
        "attest-exit",
        "The kit writes the check-out a one-shot harness could not (dag-11, F1). A seat is\n"
        "EXIT-ATTESTABLE when the sensor reports it in state.json's roster_absent, its descriptor\n"
        "declares `mode: one-shot`, it has no check-out of its own, no live lifecycle executor\n"
        "holds it, and the absence has held longer than one full sensor cadence. It then hands\n"
        "the SUPERVISOR the evidence it witnessed and the supervisor stamps the ending: a seat\n"
        "that declared `done`/`incomplete` has that declaration stand and is reaped; a process\n"
        "that died declaring nothing is `failed` with a mandatory reason class. This door stamps\n"
        "nothing of its own [spec-supervisor §3]. BARE = report only.",
        "example:\n"
        "  supervise attest-exit                    # report every candidate, write nothing\n"
        "  supervise attest-exit --seat oc2 --go    # act on one\n"
        "next: supervise ready-seats — a `failed` row advances no edge until the leader "
        "relaunches the seat")
    s.add_argument("--seat", help="one seat to consider; default is every roster_absent candidate")
    # ── W1, THE DAEMON-LANE ARM. `--session` is the ROW KEY and never a filter: it selects the one
    # row the caller opened, which is what keeps a close off a concurrent sitting's live row.
    s.add_argument("--session", metavar="ID",
                   help="(daemon lane) close the sessions.csv row carrying THIS session-id — the "
                        "id the daemon itself wrote at spawn. Checkout has already written any "
                        "ending the seat declared for itself; this arm hands the supervisor the "
                        "evidence for a death no seat could witness. No tmux, no sensor "
                        "snapshot, no name matching")
    s.add_argument("--force-dead", action="store_true",
                   help="(daemon lane, with --session) the CALLER witnessed the process exit, so "
                        "skip the pid liveness re-check. For the engine's enforce/kill arms, "
                        "which observed the death directly; never for a human")
    # The ONE fact only the observer holds. `reason_class=crash` REQUIRES an evidence pointer
    # naming the observed death (spec-state-store §1.4, §4.5), and neither the exit code nor the
    # daemon's log path is visible from inside this process — so the witness passes them in.
    # Absent, the stamp falls back to the transcript path, which is a weaker pointer, never none.
    s.add_argument("--evidence", metavar="TEXT", default="",
                   help="(daemon lane) the witnessed-death evidence pointer — exit code plus the "
                        "transcript-tail path. Passed to the supervisor and stored verbatim on "
                        "the `failed`/`crash` row it stamps")
    s.add_argument("--go", action="store_true",
                   help="ACT: export, flip the roster row, close the session row, and hand the "
                        "supervisor the evidence it stamps the ending from")
    s.set_defaults(func=attest.cmd_attest_exit)

    s = command(
        "rule-guard",
        "Record YOUR OWN seat's value for a guarded `after` member's guard — the KEY that ships\n"
        "with the guard GATE (`r-gate-ships-with-its-own-key`). A guarded edge\n"
        "`<seat>[<key>=<value>]` needs TWO things: that seat's own `done` check-out, AND a\n"
        "recorded value for the guard. A GUARD NEVER AUTO-SATISFIES — with nothing on record the\n"
        "edge stays BLOCKED, which is why writing one is an act with a name and a writer.\n"
        "⚠ THE SEAT NAMED IN THE PAIR WRITES IT, AND NO OTHER SEAT MAY: the value is a fact about\n"
        "THAT seat's own work and nobody else witnessed it. `--source` is MANDATORY: a value with\n"
        "no citation of where it was measured is indistinguishable from a guess. Refuses a seat\n"
        "with no taskforce.csv row, and a (seat, key) no live `after` member references. Appends\n"
        "to coordination/guard-values.csv, last row per (seat, key) wins. BARE = report only.",
        "example:\n"
        "  coordinate rule-guard k3 retirement-safe=yes --source \"record.md §1\"        # report\n"
        "  coordinate rule-guard k3 retirement-safe=yes --source \"record.md §1\" --go   # record\n"
        "next: coordinate checkout — a `done` checkout is REFUSED while a guard you owe is "
        "unwritten, and this discharges that debt; the guarded edge then reads this value and "
        "still requires your own `done`")
    s.add_argument("seat", help="the seat the guard is ABOUT — the name INSIDE the member token, "
                                "never the successor being unblocked. It must be YOU: the seat "
                                "named here is the only party admitted to write its own value")
    s.add_argument("guard", metavar="KEY=VALUE",
                   help="the guard's two halves, e.g. `retirement-safe=yes`")
    s.add_argument("--source", help="MANDATORY — a ledger anchor, record path or message id "
                                    "citing where this value was measured or ruled")
    s.add_argument("--go", action="store_true",
                   help="ACT: append the ruling to guard-values.csv; without it nothing is written")
    add_identity_flags(s)
    s.set_defaults(func=attest.cmd_rule_guard)

    s = command(
        "ready-seats",
        "The ready-SEAT frontier, recomputed from disk (dag-10). A seat is READY when it has no\n"
        "check-out of its own, no ACTIVE roster row, a descriptor on disk, and EVERY `after`\n"
        "predecessor in taskforce.csv carries a check-out with disposition `done`. Only `done`\n"
        "advances an edge — `renew`, `revive`, `failed` and the absence of a check-out all leave\n"
        "the successor BLOCKED. A GUARDED member `<seat>[<key>=<value>]` needs that `done` AND a\n"
        "matching recorded value (coordinate rule-guard); an ALTERNATE `a|b` is satisfied when ANY\n"
        "ONE member is. Reads workers.md, the ending store and sessions.csv; when the\n"
        "last two disagree about one seat it reports SKEW for THAT seat rather than picking a\n"
        "winner — that seat and its dependents are held, the rest of the goal keeps advancing,\n"
        "and the exit status stays 0 (Q2a).\n"
        "\n"
        "DEAD vs BLOCKED (D22) — every row also carries a boolean `dead`, and the census names\n"
        "the dead seats. BLOCKED means an `after` member is unsatisfied TODAY. DEAD means it can\n"
        "NEVER be satisfied: a guarded member whose predecessor already FINISHED having ruled a\n"
        "different value (`coordinate rule-guard` writes that ruling, and a finished seat's\n"
        "ruling does not change), or anything downstream of such a seat. That is the ordinary\n"
        "shape of a `planning-mode` fork — a taskforce registers BOTH variants and the lane runs\n"
        "one, so the other branch is dead BY DESIGN and is not a defect. An UNRULED guard is NOT\n"
        "dead (the structurer has not run), nor is a predecessor that has not finished; an\n"
        "alternate `a|b` is dead only when EVERY limb is. ⚠ A DEAD SEAT IS NOT PENDING WORK: no\n"
        "consumer may count it toward a frozen/stalled goal, retry it, or alarm on it. It is\n"
        "DERIVED at read time and stored nowhere.\n"
        "\n"
        "READ-ONLY: launches nothing, writes nothing, messages nobody.",
        "example:\n"
        "  supervise ready-seats\n"
        "  supervise ready-seats --json\n"
        "  supervise ready-seats --explain execution-strategist\n"
        "next: launch what it reports READY — `supervise launch --only <seat>`")
    s.add_argument("--json", action="store_true",
                   help="the same rows as JSON, each carrying its verdict, reason, disposition, "
                        "source and `seed` (the resolved absolute paths of the declared outputs "
                        "of the predecessors that satisfied it; [] on a root) and `dead` (D22: "
                        "true when its `after` can NEVER be satisfied, so it is blocked forever "
                        "and is NOT pending work) — so a machine consumer never parses the reason "
                        "text")
    s.add_argument("--explain", metavar="SEAT",
                   help="print the full predicate evaluation for ONE seat, term by term")
    # Q2a: the OPT-IN back to the pre-2026-08-18 whole-goal fail-close, for a caller that reads the
    # exit status and not the rows. Opt-IN and not opt-out because the default it replaced froze 65
    # healthy seats over one disputed one, and a shell caller that never heard of skew must not
    # inherit that. Refusals (unreadable package, bad argv, a crash) exit non-zero either way.
    s.add_argument("--fail-on-skew", action="store_true",
                   help="exit 1 when ANY seat reports SKEW, instead of reporting it per-seat and "
                        "exiting 0. The rows are identical either way — this only changes the "
                        "exit status, for a caller that cannot parse them")
    s.set_defaults(func=ready.cmd_ready_seats)

    s = command(
        "boot-prompt",
        "Print ONE seat's boot prompt: the exact bytes `launch` writes to that seat's prompt file,\n"
        "composed from its descriptor by the ONE composer both launchers share. For a LAUNCHER\n"
        "THAT IS NOT `launch` — the daemon's seeding pass — which enqueues the seat WITH this text\n"
        "so its harness boots on instructions instead of empty stdin. A seat with no descriptor on\n"
        "disk is REFUSED by name: an empty prompt is never printed, because an empty prompt is the\n"
        "defect this verb exists to close. READ-ONLY on the package: composes and prints, opens\n"
        "no pane, writes no prompt file, wakes nobody.",
        "example:\n"
        "  supervise --package /abs/path/to/goal boot-prompt plan-interviewer\n"
        "next: the caller launches that seat with these bytes as its prompt — this verb never does")
    s.add_argument("seat", metavar="SEAT",
                   help="the TARGET seat whose boot prompt to print, as in its descriptor's "
                        "`agent:` key — never the caller")
    s.add_argument("--lane", choices=("console", "daemon"), default="console",
                   help="which lane will carry this seat. BOTH lanes are instructed to check in "
                        "and to check out (F1, 2026-08-17); `daemon` states that its check-in is "
                        "PANELESS — it registers against the seat's already-open sessions.csv row "
                        "instead of a tmux pane — that no wake can reach it, and where its "
                        "session-id is readable. Default `console`")
    s.set_defaults(func=launch.cmd_boot_prompt)

    s = command(
        "gateway-status",
        "Task 7.57 (DETECT half only). Reports whether an ignite daemon serves THIS\n"
        "workspace on THIS machine (.rbtv/modules/ignite/server.json) — a pure file read,\n"
        "always safe. Does NOT route coordination send/read through the gateway: that is\n"
        "RULED NOT MET (fork 1) — the gateway has no addressed-message door yet.\n"
        "checkin/send/read/pending/... never call this and are unaffected by it.",
        "example:\n"
        "  coordinate gateway-status            # detection only, zero network\n"
        "  coordinate gateway-status --probe    # ALSO makes one live read-only `inspect`\n"
        "                                       # call to prove the authenticated wire\n"
        "next: nothing — informational; coordination messages still use the run package")
    s.add_argument("--probe", action="store_true",
                   help="explicit opt-in (inert by default, Fork 2 ruled): make one live "
                        "read-only `inspect` call against the detected gateway")
    s.set_defaults(func=cmd_gateway_status)

    s = command(
        "secret-add",
        "Append ONE NAME to the workspace env file from a drop file. Masters only\n"
        "(goal-master, channel-master, console/owner). Identity is the proven F-8 ladder —\n"
        "pane, COORD_AGENT, or cgroup→roster — never a bare --as. This process is the\n"
        "CLIENT: it sends NAME and the drop-file PATH to the daemon, which (out of cage)\n"
        "reads the value, appends, and deletes the drop. The value never enters argv, the\n"
        "wire, logs, or this command's output. Append-only: an existing NAME is refused.\n"
        "Drop files under .rbtv/goals/ are refused. No update, no delete, no read-back.",
        "example:\n"
        "  coordinate secret-add GEMINI_API_KEY --from-file /path/in/the/workspace/gemini-key.txt\n"
        "next: nothing — the NAME is in the env file; the drop file is gone; there is no "
        "read-back verb")
    s.add_argument("name", metavar="NAME",
                   help="the env identifier to append (letters, digits, underscore)")
    s.add_argument("--from-file", dest="from_file", metavar="PATH", required=True,
                   help="drop file holding the value as a single line — never pass the value on argv")
    add_identity_flags(s, force=False)
    s.set_defaults(func=cmd_secret_add)

    s = command(
        "selftest",
        "Run the built-in self-test in a temp dir: no tmux, no run package, no network — every\n"
        "tmux touch is stubbed. Required to exit 0 before any change to this script is used.",
        "example:\n"
        "  python3 coord.py selftest --expect-fail 'epilog index and the parser agree'\n"
        "next: nothing — a non-zero exit means the change is not ready")
    s.add_argument("--expect-fail", metavar="SUBSTRING", default=None,
                   help="mutation-testing: name the ONE check this mutation should break. Exits 0 "
                        "only if that check failed and every other passed — a suite that goes red "
                        "for an unrelated reason is not evidence (G-62)")
    s.set_defaults(func=cmd_selftest)

    # ---- s3-05: the HIDDEN lifecycle executor. Registered through `command()` like every other
    # subcommand — so `save-coord.py`'s parser-build gate covers it and its own -h is held to the
    # same example/next bar — but deliberately ABSENT from HELP_EPILOG, which IS the command list a
    # seat reads. `HIDDEN_COMMANDS` is what tells the epilog-vs-parser check that the omission is
    # intended rather than drift. No seat ever types this: `s3-09`'s caller forks it.
    #
    # ⚠ NOTE ON `help=argparse.SUPPRESS`. The task names it, and it is already in force twice over:
    # the subparsers ACTION carries `help=argparse.SUPPRESS` (so the positional block renders no
    # command at all) and `command()` deliberately passes no `help=` to `add_parser`. Widening
    # `command()`'s signature to pass a third suppression would change no rendered byte.
    s = command(
        "lifecycle-exec",
        "INTERNAL, NOT FOR HAND USE — the detached lifecycle executor. A fresh subprocess the\n"
        "caller forks so a seat's session rotation runs OUT OF the pane that is dying. Pure code,\n"
        "no agent in the path, NO seat identity: it never resolves a role, because by the time it\n"
        "runs the act is already authorised.\n"
        "\n"
        "ALL ARGV, NOTHING FROM THE ENVIRONMENT — it scrubs TMUX/TMUX_PANE/COORD_AGENT/\n"
        "COORD_LAUNCH_TARGET at entry and refuses rather than guessing a tmux target.",
        "example:\n"
        "  python3 supervise.py lifecycle-exec --package /abs/run-3 --seat engineer \\\n"
        "      --disposition close --pane %37 --tmux-target %37 \\\n"
        "      --caller-pid 41190 --caller-starttime 884118\n"
        "next: nothing by hand — read the seat's marker through `coordinate status`, which names "
        "any lifecycle marker in alarm")
    # Its OWN --package, required and absolute: this executor never infers a package from cwd, a
    # run tag, or the environment. (argparse copies a subparser's values over the global ones, so
    # this flag — not the global --package — is what `base_dir` reads here.)
    s.add_argument("--package", metavar="DIR", required=True,
                   help="the run package, ABSOLUTE — the caller resolves it (package_dir) and passes it; never inferred here")
    s.add_argument("--seat", metavar="NAME", required=True,
                   help="the seat whose session is rotating")
    s.add_argument("--disposition", required=True, choices=lifecycle_exec.LIFECYCLE_DISPOSITIONS,
                   help="which lifecycle act this is — cross-verified against awaiting-close.json through LIFECYCLE_INTENT_OF: renew|close expect the intent their checkout recorded, revive (the crash arm) expects NO record at all and no stamped handoff block")
    s.add_argument("--pane", metavar="%N", default=None,
                   help="the seat's pane as the caller measured it")
    s.add_argument("--tmux-target", dest="tmux_target", metavar="ID", required=True,
                   help="explicit pane or window id for the relaunch — validated against live tmux; empty or unresolvable REFUSES, because an unresolved target lands in the most recent session, which was measured to be the live room")
    s.add_argument("--caller-pid", dest="caller_pid", type=int, metavar="P", required=True,
                   help="the forking process's pid — half of the identity pair the settle wait and the died-mid-flight evidence rest on")
    s.add_argument("--caller-starttime", dest="caller_starttime", metavar="S", required=True,
                   help="the forking process's /proc starttime — the half a recycled pid cannot forge")
    s.add_argument("--handoff-written", dest="handoff_written", choices=("0", "1"), default=None,
                   help="required on --disposition renew: the caller's assertion that it wrote a handoff block, which this executor RE-READS in memory.md before renewing")
    s.set_defaults(func=lifecycle_exec.cmd_lifecycle_exec)
    p.command_parsers = made  # so the self-test can render every command's help
    return p


def assert_argv_body_shell_safe(args):
    """S-4(b) at the ONE boundary where argv provenance is knowable: a body that arrived in THIS
    process's argv, parsed by whatever launched us.

    G-101 — these two checks used to sit inside `message_body`, where they interrogated AMBIENT
    PROCESS STATE (the parent's `comm`, the parent's pre-substitution command line) rather than the
    provenance of the body they judged. `_selftest_checks` calls `cmd_send` with synthetic
    positional bodies, which that evidence cannot tell apart from a human typing at a shell, so the
    guard refused the suite's own sends and `sys.exit(1)` tore the run down at check 17 of 303. The
    gate every seat must pass before saving this file was therefore RED — and the deeper fault was
    that its verdict was decided by the SHAPE OF THE CALLER'S INVOCATION: a shell that execs itself
    away on a simple command, or a `timeout`/`env` wrapper, leaves a non-shell parent and the guard
    never fires at all. Two independent verifiers reported this gate GREEN from wrapped invocations
    while it was RED from plain ones, and re-derivation — the campaign's standard remedy — cannot
    detect that, because both re-derivations were honest and reinforced each other. Only VARYING
    THE INVOCATION exposes it.

    Deciding it here, after parsing and before dispatch, is the fix rather than a flag: a real CLI
    body is the only thing that can be present at this point. Synthetic and in-process callers
    (`watch.py`, the daemon jobs, the self-test) build a Namespace and call the command function
    directly, so they never reach this boundary and never pay for a hazard they cannot have — which
    is what `CLI_INVOCATION` was always trying to express.
    """
    # `verdict` carries a positional body through `message_body` exactly as `send` does, so it
    # is judged at this same boundary rather than growing a second copy of the guard.
    if not (CLI_INVOCATION and getattr(args, "func", None) in (cmd_send, cmd_verdict)):
        return
    body = getattr(args, "message", None)
    if not body:
        return      # --file / --file - / no body: nothing a shell could have eaten
    eaten = substitution_eaten(body)
    if eaten and not getattr(args, "force", False):
        refuse(
            "input",
            f"your shell SUBSTITUTED {' and '.join(eaten)} in this body before "
            f"coord.py ever saw it — what you are about to log is the OUTPUT of a command "
            f"that actually RAN on your box, not the text you wrote. coord.py cannot "
            f"repair it: the original characters are already gone from argv.\n"
            f"Send it via --file (or --file - with a quoted heredoc) — the only form a "
            f"shell cannot eat:\n"
            f"  cat > /tmp/msg.txt <<'EOF'\n  ...your text...\n  EOF\n"
            f"  {coord_invocation(args)} send {getattr(args, 'to', '<to>')} "
            f"--type {getattr(args, 'type', '<type>')} --file /tmp/msg.txt\n"
            f"your shell's original line, for reference:\n  {shell_source_line()[:400]}\n"
            f"override (you are certain the substitution was harmless): --force",
            1)
    # G-101 residual (leader #76): the parent-process test is GONE, deliberately. It asked "was
    # our argv parsed by a shell", and any exec-away wrapper — `timeout`, `env`, `nice`, `xargs`
    # — answers no while a shell parsed the line anyway. Measured after the boundary move:
    # `coordinate send x "body"` refused, `timeout 30 coordinate send x "body"` ACCEPTED, and
    # `timeout 30 coordinate send x "text $(echo EATEN)"` put EATEN into the permanent log.
    # Wrappers are not exotic — a leader reaching for `timeout` on anything that might hang
    # produced that corruption twice in one hour. So the rule is now unconditional at this
    # boundary: a positional body pays an explicit `--inline`, whatever launched us. That is
    # S-4(b)'s own design (default safe; the unsafe path pays an assertion) with the inference
    # removed, and it costs nothing real — every programmatic caller either goes in-process
    # (goal-watcher-job calls cmd_send directly) or already uses --file (the probes).
    if not getattr(args, "inline", False):
        refuse(
            "input",
            f"this body was typed on a shell command line, and a shell eats "
            f"backticks and $(...) BEFORE coord.py can see them — the corruption is "
            f"undetectable after the fact and it has silently rewritten this room's "
            # The count that used to sit here ("three times") had no maintainer and no way to be
            # checked at read time — permanent text asserting a number that only ever grows. It
            # is the drift the run already ruled on in its evidence layer, wearing a refusal's
            # clothes. The force of the sentence was never the number; it is that the authors
            # KNEW.
            f"record repeatedly, each time by an author who knew about it.\n"
            f"Shell-safe (cannot be eaten):\n"
            f"  cat > /tmp/msg.txt <<'EOF'\n  ...your text...\n  EOF\n"
            f"  {coord_invocation(args)} send {getattr(args, 'to', '<to>')} "
            f"--type {getattr(args, 'type', '<type>')} --file /tmp/msg.txt\n"
            f"Short body with no backticks, quotes or $ in it? Add --inline and it is "
            f"sent as typed.",
            1)

def main(door=COORDINATION_DOOR):
    # S-4(b): only a real CLI invocation had its argv parsed by a shell. watch.py and the
    # daemon jobs call cmd_send() IN-PROCESS with a Namespace — no argv, no shell, never
    # exposed — and must not pay for a hazard they cannot have. This flag is the difference,
    # and it is set HERE rather than inferred from the parent process, because an in-process
    # caller started from a shell has a shell parent too and would otherwise be caught.
    global CLI_INVOCATION
    CLI_INVOCATION = True
    args = build_parser(door).parse_args()
    set_pretty(args)
    # S-4(b)/G-101 — argv provenance is a property of the INVOCATION, so it is judged here,
    # at the boundary, and never inside a function that also serves synthetic callers.
    assert_argv_body_shell_safe(args)
    args.func(args)
