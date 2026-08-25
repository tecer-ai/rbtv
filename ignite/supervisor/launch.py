# ---------- launch / lifecycle ----------

def frontmatter_text(text):
    """The descriptor's frontmatter block, or `None` when it has none.

    ⚠ BYTE-FOR-BYTE THE SPAN `discover_workers` READS — `startswith("---")`, then `find("\\n---",
    3)`. That equality is load-bearing, not tidiness: `descriptor_yaml_findings` hands this block
    to a real YAML parser while every other check in this file reads the SAME block with regexes,
    and a check that parsed a different span from the one the kit acts on would be reporting about
    a file nobody reads.

    ⚠ THREE OTHER SITES STILL INLINE THIS SPLIT (`discover_workers`, the descriptor-name reader
    around :293, the addressable-row reader around :2872). They are NOT rewired here — that is a
    sweep with its own blast radius across three audited readers, and this task's scope is the
    parse check. Filed as a loose end; until it is done, an edit to the split must reach four
    places."""
    if not text.startswith("---"):
        return None
    fm_end = text.find("\n---", 3)
    return None if fm_end == -1 else text[:fm_end]


def descriptor_yaml_findings(wdir):
    """[(seat, path, error)] — every descriptor whose frontmatter NO YAML READER CAN LOAD (G-256).

    THE DEFECT THIS CLOSES, and it is a green that means nothing: every structural check in this
    file reads frontmatter with REGEXES, and a regex is delighted by a document YAML rejects. So a
    descriptor no parser can load passed the whole structural audit — while any consumer that
    parses it properly (the daemon, a materializer, a linter) fails on it. Two such files were
    measured live on run-2, and the audit reported them clean.

    THE KNOWN SHAPE, worth naming because the step-1 authoring wave hit it FOUR times: an
    UNQUOTED COLON-SPACE inside a `description:` value silently breaks YAML — `description: fix
    the gate: threading` is a mapping value where a mapping is not allowed — while every
    structural check keeps passing.

    A parse failure is a FINDING: named, with the file path and THE PARSER'S OWN ERROR. Never a
    silent skip, never a pass. And PyYAML's absence is itself reported as a finding rather than
    skipped — a check that cannot run and says nothing is indistinguishable from a check that ran
    and found nothing, which is this very defect one level up."""
    out = []
    try:
        import yaml
    except ImportError as exc:                      # noqa: BLE001 — reported, never swallowed
        return [("(all seats)", wdir,
                 f"the YAML parse check COULD NOT RUN — {exc}. Reported as a finding rather than "
                 f"skipped. Install PyYAML.")]
    for path in briefing_files(wdir):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            out.append((path.parent.name or path.stem, path, f"unreadable: {exc}"))
            continue
        fm = frontmatter_text(text)
        if fm is None:
            continue                                 # no frontmatter is a DIFFERENT finding
        try:
            yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            out.append((path.parent.name or path.stem, path, " ".join(str(exc).split())))
    return out


def discover_workers(wdir):
    """Every briefing with an `agent:` frontmatter key — leader INCLUDED, so an explicit
    by-name `launch --only leader` or `close-seat leader --renew` can target it. A bare
    mass `launch` still never boots leader: seats_by_name filters it from the no-names sweep.

    Returns per-seat dicts: agent, agent_type (str — the DECLARED type, "" when the descriptor
    declares none; 7.278's capacity term sizes `counting.counts_toward_cap` off this and nothing
    else), briefing, harness, model, effort, cwd, window, ephemeral,
    ctx_refresh (int|None — the seat's own context-refresh threshold),
    folder (the seat's worker folder in folder form, else None)."""
    found = []
    for p in briefing_files(wdir):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm_end = text.find("\n---", 3)
        if fm_end == -1:
            continue
        fm = text[:fm_end]
        m = FM_KEY["agent"].search(fm)
        if not m:
            continue
        # G-14: the seat.md (KG run-folder) form resolved NO folder, so `memory.md` was invisible
        # to boot_prompt and every renewed PERSISTENT seat booted without being told to read its
        # own memory — the one artifact a close exists to produce. Both briefing names count.
        folder = p.parent if p.name in ("agent.md", "seat.md") and p.parent != wdir else None
        mt = FM_KEY["agent_type"].search(fm)   # 7.278 (C3) — additive; no existing key changes
        mh = FM_KEY["harness"].search(fm)
        mm = FM_KEY["model"].search(fm)
        me = FM_KEY["effort"].search(fm)
        mc = FM_KEY["cwd"].search(fm)
        mr = FM_KEY["ctx-refresh"].search(fm)
        harness = mh.group(1) if mh else "claude"
        # A RELATIVE `cwd:` reaches `tmux -c` VERBATIM, and tmux resolves it against nothing —
        # it silently falls back to $HOME and the seat boots in the wrong tree, reporting
        # success. Absolutized HERE, at the ONE parse point every consumer reads (respawn,
        # new-window, split), so no consumer needs its own guard. An ABSOLUTE value passes
        # through BYTE-IDENTICAL — deliberately NOT normalized, because other code compares
        # these strings. Measured: one hand-edited descriptor of 408 carried a relative value.
        cwd = mc.group(1) if mc else (str(folder) if folder else VAULT_ROOT)
        if not os.path.isabs(cwd):
            cwd = os.path.join(VAULT_ROOT, cwd)
        out_declared, out_tokens, out_chat = iospec_outputs(text)
        found.append({
            "agent": m.group(1), "briefing": p, "harness": harness,
            # 7.278 (C3): "" means the descriptor DECLARED NOTHING. Kept distinguishable from a
            # declared value on purpose — the capacity term prints the undeclared ones by name.
            "agent_type": mt.group(1) if mt else "",
            # ⚠ AN UNDECLARED CAST IS `""` — NEVER A PLAN DEFAULT, on either field. A claude seat
            # with no `model:` used to be handed DEFAULT_MODEL and a seat with no `effort:` was
            # handed DEFAULT_EFFORT, so an UNCAST seat launched silently on somebody else's
            # choice and the record said otherwise. The daemon door already refuses exactly this
            # (`supervisor/launch-profiles/catalog.js`, `E_UNCAST_SEAT`: "declares no cast — `harness:` and
            # `model:` must BOTH be present"); with the fallbacks gone, `validate_seat` refuses it
            # here too, on the rules that were already written. The CONSTANTS stay: `DEFAULT_EFFORT`
            # is the closer pane's OWN authored literal (see `closer` composition), which is a
            # choice this kit makes about a seat it invents, not a fallback for one it read.
            "model": mm.group(1) if mm else "",
            "effort": me.group(1) if me else "",
            "cwd": cwd,
            "window": _fm_window(fm),
            "ephemeral": _fm_yes(fm, "ephemeral"),
            "ctx_refresh": int(mr.group(1)) if mr else None,
            "mode": (FM_KEY["mode"].search(fm).group(1)
                     if FM_KEY["mode"].search(fm) else ""),
            "folder": folder,
            "mechanical_close": _fm_mechanical_close(fm),
            # 7.676/D3: declared outputs are read off the BODY's io-spec `## Outputs` block via
            # `iospec_outputs` (the shared resolver), at THIS one parse point because `cwd` is
            # absolutized here and a declared output resolves against it. Parsing the descriptor
            # twice would be two readers of one file (PRIN-11). The tuple unpacks below:
            # `outputs_declared` carries the block-exists bit separately so a ZERO-TOKEN prose
            # block classifies loudly (`outputs-undeclarable`) instead of reading `none-declared`.
            "outputs": out_tokens,
            "outputs_declared": out_declared,
            # D36: the typed NON-FILE declaration, carried beside the block-exists bit so the
            # check-out can tell "declared nothing checkable" from "declared conversation".
            "outputs_chat": out_chat,
            # 7.711/D3: the RETIRED-key tripwire, read at the same parse point.
            "outputs_defect": _fm_outputs_defect(fm),
        })
    return found


# ---------- structural descriptor audit (G-57) ----------
#
# G-51 refuses a LAUNCH whose descriptor disagrees with the registry — one seat, at one moment,
# on three binding fields. This is the standing sweep over the WHOLE descriptor set, and it is
# read-only: it opens no briefing body, only frontmatter and paths, because a descriptor is a
# BRIEFING and R-isolation bars a seat from reading another seat's briefing. Fields and paths are
# not prose, so nobody's instructions enter anybody's context.
#
# WHAT IT DELIBERATELY DOES NOT COVER, printed in its own output every run: a descriptor's OWNED-
# SURFACES claim and its mission narrative are prose, and the run's surface map is prose too, so no
# mechanical pass can compare them. That is the half of G-57 that bit this run — a descriptor
# claiming surfaces handed to another seat a milestone earlier — and it stays open until a
# `surfaces:` frontmatter key makes the claim a field. A clean result here is NOT a clean class.

def descriptor_findings(args):
    """[(seat, kind, detail)] — every structural divergence in the run's descriptor set."""
    wdir = workers_dir(args)
    registry = taskforce_bindings(args)
    seats = discover_workers(wdir)
    found = []
    by_name = {}
    for w in seats:
        name = w["agent"]
        if name in by_name:
            # Two descriptors claiming one name: `launch` resolves whichever it finds first, so
            # the seat that boots is decided by directory order — never by anyone's intent.
            found.append((name, "duplicate-name",
                          f"also declared by {by_name[name]} — launch would pick by walk order"))
            continue
        by_name[name] = w["briefing"]
        folder = w["folder"]
        if folder is not None and folder.name != name:
            found.append((name, "name-vs-folder",
                          f"descriptor says {name}, folder is {folder.name}"))
        cwd = Path(w["cwd"])
        if not cwd.is_dir():
            found.append((name, "cwd-missing", f"cwd does not exist: {cwd}"))
        elif folder is not None and cwd.resolve() != folder.resolve():
            found.append((name, "cwd-vs-folder",
                          f"cwd is {cwd}, seat folder is {folder}"))
        row = registry.get(name)
        if row is None:
            if registry:
                found.append((name, "no-registry-row",
                              "descriptor exists with no taskforce.csv row — nothing records "
                              "this seat's binding"))
        else:
            for field, descriptor, reg in binding_divergence(w, row):
                found.append((name, "binding-divergence",
                              f"{field}: descriptor {descriptor} | taskforce.csv {reg} "
                              f"(THE DESCRIPTOR BINDS)"))
    for name in registry:
        if name not in by_name:
            found.append((name, "no-descriptor",
                          "taskforce.csv row with no descriptor — this seat cannot launch"))
    return found


# The documents a seat is known to READ AT BOOT — its loader pair, its descriptor, its memory, and
# the handoff/state doc that proved the class (a superseded ruling sat verbatim in SEAT-STATE.md,
# read at boot and never re-read). Used ONLY to rank and mark the boot-stale report, never to
# filter it: a boot-read document under a name not listed here is still reported, just lower.
BOOT_READ_NAMES = {"seat.md", "agent.md", "memory.md", "SEAT-STATE.md", "CLAUDE.md", "AGENTS.md"}


def boot_stale_findings(args):
    """[(seat, path, mtime)] — files in a LIVE seat's folder modified after that seat checked in.

    G-61: a seat's instructions are WRITE-ONCE AT BOOT. Nothing re-reads them, so a ruling that
    invalidates a running seat's briefing reaches it only if someone notices by hand. Measured
    instance: a planner booted at 06:50 on constraints reversed at 06:52 and had no way to learn it.

    The scope is the seat's OWN FOLDER, not `seat.md` alone, because the widening that proved the
    class came from `SEAT-STATE.md` — a boot-read document that is not the descriptor. A folder IS
    the seat-scoped boot-read surface, so `memory.md`, handoff docs and successors are covered by
    construction, with no declared list to maintain and no layout decision to settle first.

    `BOOT_STALE_SKIP_DIRS` is excluded: `transcripts/` is an export target written by the close
    ceremony, and `sessions/` is the seat's own per-session scratchpad (7.96). NEITHER is read at
    boot, so a change in either says nothing about whether the seat's instructions have moved.
    ⚠ THE SCRATCHPAD EXCLUSION IS A SAFETY-DETECTOR CHANGE, NOT TIDYING. Without it this detector
    fires on every file a working seat writes — it would report ITSELF as evidence its own
    instructions went stale, at a volume that retires the alarm within a day. The genuine signal
    (`seat.md`, the briefing, a boot-read document at the seat-folder ROOT) is untouched, which is
    what the red arm in `_selftest_checks` proves in both directions.

    DELIBERATELY OVER-REPORTS, and the trade is the point: mtime moves when content does not, and
    a seat writing its OWN memory.md trips it. A false positive costs a glance; the false negative
    this replaces cost the run a live seat planning against two dead constraints.
    """
    base = base_dir(args)
    _, _, rows = load_workers(base)
    wdir = workers_dir(args)
    out = []
    for name in dict.fromkeys(r["agent"] for r in rows):
        row = current_row(rows, name)
        if not row or row.get("active") != "yes":
            continue
        try:
            since = datetime.strptime(row.get("checkin", "").strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            continue  # an unparseable checkin stamp is not evidence of staleness either way
        folder = wdir / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            parts = path.relative_to(folder).parts
            if not path.is_file() or any(d in parts for d in BOOT_STALE_SKIP_DIRS):
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                continue
            if mtime > since:
                out.append((name, path.relative_to(folder), mtime))
    return out


def cmd_descriptors(args):
    """Read-only structural audit of every seat descriptor (G-57). Opens no briefing body."""
    findings = descriptor_findings(args)
    wdir = workers_dir(args)
    print(f"{c('descriptors:', C_LABEL)} {wdir}")
    print(f"{c('registry:', C_LABEL)} {package_dir(args) / 'taskforce.csv'}")
    if findings:
        for seat, kind, detail in sorted(findings):
            print(f"  {c(seat, C_DEAD)}  {kind}: {detail}")
    print(f"\nstructural findings: {len(findings)}")
    # The bound is printed on EVERY run, clean or not — the leader's own ruling generalised: a
    # clean result must never be readable as a clean class.
    print("bound: frontmatter fields and paths ONLY. A stale owned-surfaces claim or a stale "
          "mission narrative is PROSE and is NOT checked here — zero findings does not mean the "
          "descriptors are true.")

    # dag-19 / G-256: its OWN section, appended after every line this command already printed,
    # so the pre-existing output is byte-identical to what it was before the check existed.
    yml = descriptor_yaml_findings(wdir)
    print(f"\n{c('yaml-parse (G-256):', C_LABEL)} descriptors NO YAML READER CAN LOAD")
    for _y_seat, _y_path, _y_detail in sorted(yml, key=lambda f: str(f[1])):
        print(f"  {c(_y_seat, C_DEAD)}  {_y_path}: {_y_detail}")
    print(f"yaml-parse findings: {len(yml)}")
    print("bound: the FRONTMATTER BLOCK ONLY, parsed by the same reader a consumer would use. "
          "Every other check on this command reads that block with REGEXES, which are delighted "
          "by a document YAML rejects — that is the gap this closes, and it closes only that.")

    stale = boot_stale_findings(args)
    # Measured on this run's first live pass: 11 findings, 10 of them a seat writing its OWN
    # outputs. Full coverage is deliberate and kept — but an alarm that rings ten times per real
    # signal is one nobody reads, so boot-read NAMES are ranked first and marked. This is a DISPLAY
    # heuristic, never a filter: nothing is hidden, and a boot-read document under a name not on
    # the list still appears, just lower.
    ranked = sorted(stale, key=lambda f: (f[1].name not in BOOT_READ_NAMES, f[0], str(f[1])))
    print(f"\n{c('boot-stale (G-61):', C_LABEL)} files changed since the LIVE seat read them")
    for name, rel, mtime in ranked:
        mark = "BOOT-READ" if rel.name in BOOT_READ_NAMES else "also"
        print(f"  {c(name, C_DEAD)}  [{mark}] {rel} modified {mtime:%Y-%m-%d %H:%M} — after that "
              f"seat checked in; it is still running the version it booted on")
    high = sum(1 for _, rel, _ in stale if rel.name in BOOT_READ_NAMES)
    print(f"boot-stale findings: {len(stale)} "
          f"({high} BOOT-READ by name, {len(stale) - high} other)")
    print(f"bound: MTIME, not content, over the seat's folder minus "
          f"{'/, '.join(BOOT_STALE_SKIP_DIRS)}/ — it over-reports "
          "(a seat writing its own memory.md trips it) and it CANNOT see a ruling that invalidates "
          "a seat's instructions without anyone editing its files. Zero here is not proof a seat "
          "is current.")
    sys.exit(1 if (findings or stale or yml) else 0)


# ---------- descriptor vs taskforce.csv (G-51) ----------
#
# The SEAT DESCRIPTOR binds: `launch` and `close-seat --renew` build the harness command from its
# frontmatter. `taskforce.csv` is the run's binding REGISTRY — and until this check, the kit never
# opened it (`grep -n taskforce coord.py` returned nothing), so the two could disagree silently and
# permanently. They did: a seat re-bound in the registry after an owner-departure event still
# launched on its old model, because a CSV row cannot bind anything. That defect appeared THREE
# times in one run before it was named once.
#
# This does not make the CSV authoritative — it makes a DISAGREEMENT impossible to launch through
# without seeing it. The refusal says which side binds, because a 3am reader who is only told the
# two files differ has been handed the confusion, not the answer.

def taskforce_bindings(args):
    """{seat: {harness, model, effort}} from the run package's taskforce.csv — {} when the file is
    absent (a legacy `workers/` package has no registry, and its seats must still launch)."""
    path = package_dir(args) / "taskforce.csv"
    if not path.is_file():
        return {}
    try:
        rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    except (OSError, ValueError, csv.Error):
        return {}
    out = {}
    for r in rows:
        seat = (r.get("seat") or "").strip()
        if seat:
            out[seat] = {k: (r.get(k) or "").strip() for k in ("harness", "model", "effort")}
    return out


def registered_seats(pkg):
    """Seat names this package's registers know — taskforce.csv `seat` ∪ sessions.csv `seat`.

    Empty or absent file → empty contribution. Never raises. Folder presence is not consulted.
    """
    names = set()
    try:
        root = Path(pkg)
    except (TypeError, ValueError):
        return names
    for path in (root / "taskforce.csv", sessions_csv(root)):
        try:
            header, rows = read_csv_table(path, [])
        except Exception:
            continue
        if "seat" not in header:
            continue
        idx = header.index("seat")
        for r in rows:
            name = (r[idx] if idx < len(r) else "").strip() if r else ""
            if name:
                names.add(name)
    return names


def binding_divergence(w, row):
    """[(field, descriptor_value, registry_value)] where the two disagree.

    A BLANK registry cell means "not stated" and is skipped — the opencode verification seats
    legitimately carry no `effort`, and treating blank as a value would refuse every one of them.
    """
    out = []
    for field in ("harness", "model", "effort"):
        registry = (row.get(field) or "").strip()
        if not registry:
            continue
        descriptor = (w.get(field) or "").strip()
        if descriptor != registry:
            out.append((field, descriptor or "(unset)", registry))
    return out


def check_bindings(args, workers, command):
    """REFUSE when a seat's descriptor disagrees with its taskforce.csv row — or has NO row at all
    while the registry HAS rows (G-51; the missing-row half is 7.99). `--force` overrides, as on
    every other refusal here.

    7.99, measured by dag-05: this loop used to compare only the rows that EXIST, so a seat whose
    registry row was lost — a crash between materialize's two steps, a hand-deletion — passed the
    binding check by having nothing to check. `coordinate descriptors` names that half-state
    (`no-registry-row`) and gates NOTHING, so the launch went through unbound. A MISSING row is not
    a weaker divergence, it is the absence of the record the check exists to compare against; the
    registry being non-empty is what makes the absence a defect rather than a legacy package.
    """
    registry = taskforce_bindings(args)
    if not registry:
        return
    problems = []
    missing = []
    for w in workers:
        row = registry.get(w["agent"])
        if row is None:
            missing.append(w)
            continue
        diff = binding_divergence(w, row)
        if diff:
            problems.append((w, diff))
    if not (problems or missing) or getattr(args, "force", False):
        for w, diff in problems:
            fields = ", ".join(f"{f}: descriptor {d} vs registry {r}" for f, d, r in diff)
            print(c(f"WARNING --force: {w['agent']} binds from its DESCRIPTOR ({fields})",
                    C_DEAD), file=sys.stderr)
        for w in missing:
            print(c(f"WARNING --force: {w['agent']} has NO taskforce.csv row (no-registry-row) — "
                    f"it binds from its DESCRIPTOR and the registry records nothing", C_DEAD),
                  file=sys.stderr)
        return
    lines = []
    for w, diff in problems:
        lines.append(f"{w['agent']}:")
        for field, descriptor, registry_value in diff:
            lines.append(f"    {field}: descriptor says {descriptor} | taskforce.csv says "
                         f"{registry_value}")
        lines.append(f"    descriptor: {w['briefing']}")
    for w in missing:
        lines.append(f"{w['agent']}: NO taskforce.csv ROW (no-registry-row)")
        lines.append(f"    the registry carries {len(registry)} row(s) and none of them is this "
                     f"seat's — nothing records what it should bind, so there is nothing to check "
                     f"the descriptor against")
        lines.append(f"    descriptor: {w['briefing']}")
    detail = "\n  ".join(lines)
    refuse(
        "state",
        f"`{command}` — {len(problems) + len(missing)} seat(s) fail the run's registry check:\n  "
        f"{detail}\n"
        f"  registry: {package_dir(args) / 'taskforce.csv'}\n"
        f"THE DESCRIPTOR IS AUTHORITATIVE — it is what the harness command is built from, so "
        f"launching now would bind the DESCRIPTOR's value and the taskforce.csv row would stay "
        f"a wrong record.\n"
        f"Fix whichever is wrong: edit the DESCRIPTOR to change what actually binds, or the CSV "
        f"row to correct the record. A seat with NO row needs one added (or the whole registry "
        f"removed, which is the legacy `workers/` package this check skips). Then re-run.\n"
        f"--force launches on the descriptor's value anyway and says so.",
        2)


def identity_prefix(agent):
    """The shell-env prefix that gives a launched seat its identity (T1), plus its `TMPDIR`
    redirect (7.400) off the quota'd tmpfs. Every command the seat then runs resolves
    `COORD_AGENT` — it never types its own name, and cannot mistype another seat's — and every
    tmp write it or its harness makes lands on `/dev/sda1` at AGENT_TMPDIR instead."""
    return f"COORD_AGENT={shlex.quote(agent)} TMPDIR={shlex.quote(AGENT_TMPDIR)} "


CLAUDE_MODEL_ALIASES = ("opus", "sonnet", "haiku", "fable")
OPENCODE_MODEL_RE = re.compile(r"[^/\s]+/[^/\s]+\Z")


# ---------- the seat's cast -> its PROFILE'S OWN effort dial (envelope/spawn-profiles.yaml) --------
#
# ⚑ THE FRAGMENT IS AUTHORED PER PROFILE, NEVER HERE. `--effort {w['effort']}` was hardcoded on the
# claude branch of `harness_command` and nowhere else, so a codex seat (a real 3-rung ladder), a
# kimi seat and all seven opencode seats launched with their declared effort SILENTLY DROPPED. The
# daemon door composes the same thing from `effort.argv` in `envelope/spawn-profiles.yaml`
# (`supervisor/launch-profiles/profiles.js#resolveEffort`); this reads that same authored list, so the two
# doors agree BY CONSTRUCTION and the next harness added to that file is honoured here with no code
# change. `probe-bindings.py`'s both-doors sweep is what holds the two spellings together.
#
# ⚠ THE LADDER IS READ BY `bindings.py#spec_effort` AND BY NOTHING ELSE. Two scrapers of these
# same bytes already disagreed on identical input (measured 2026-08-11 — one read INERT where the
# other read a five-rung ladder), so this file adds no third opinion on the rungs. What it reads for
# itself is only that spec's `effort.argv`.
#
# ⚠ THE THIRD DERIVATION OF (harness, model) IS GONE (`#d-abolish-profile-names`, 2026-08-12). This
# function used to SCAN every profile block for one whose argv pinned the seat's pair, because the
# document was keyed by an arbitrary name. `launch-specs:` is keyed by the pair, so the lookup is
# now a two-level dict access and the law it re-implemented (harness = basename(argv[0]); model =
# the token after the first `--model`/`-m`) exists in exactly one place: the daemon's config-LOAD
# guard `supervisor/launch-profiles/profiles.js#validateSpecKey`. The recursion hazard that forced the third
# copy — both siblings reach the answer only through a call that re-enters `validate_seat` — is
# moot now that no call is needed at all.
#
# ⚠ IMPORT DIRECTION — S-4. `bindings.py` imports `validate_seat` FROM this file, lazily, inside its
# own function. This import mirrors that exactly: LAZY, inside the function, and FAIL-SOFT. A
# module-level import would risk that cycle AND drag PyYAML into the file every seat's messaging
# runs through — an import-time failure there takes the whole room's comms down, including every
# recovery path. When anything about the read fails, the answer is "no dial", which is byte-for-byte
# the behaviour every harness but claude already had.
@functools.lru_cache(maxsize=4)
def _profiles_doc(path, _stamp):
    """The parsed profiles document, memoized on its own (mtime_ns, size).

    ponytail: MEASURED, not anticipated. `yaml.safe_load` on this document costs ~121 ms on the VPS
    (pure-Python PyYAML, ~1400 lines), and `validate_seat` + `harness_command` are called per seat
    on every launch, every dry-run display and ~100 times in the selftest — 25 s added to a probe
    that already runs 129 s against a 180 s timeout. Ceiling: a rewrite inside the same nanosecond
    AND at the same size reads stale. Upgrade path: hash the bytes, the day that is cheaper than
    parsing them (today it is not — reading 60 KB to hash it is most of the cost of parsing it)."""
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


@functools.lru_cache(maxsize=64)
def _spec_rungs(harness, model, path, _stamp):
    """This launch spec's ladder as a tuple — `bindings.py#spec_effort`'s three-way answer, memoized
    per spec on the same stamp. The caller has already put its directory on `sys.path`."""
    from bindings import spec_effort
    rungs = spec_effort(harness, model, path)
    return None if rungs is None else tuple(rungs)


def _cast_effort(w):
    """`(rungs, fragment)` for this seat's cast, both read off the profile that runs it.

    `rungs` is `bindings.py#spec_effort`'s three-way answer, forwarded verbatim: `None` = no dial
    (or this workspace declares no launch spec for the pair), `[]` = an INERT dial (G-270 — accepted
    and reported, never silently dropped), `[...]` = a real ladder. `fragment` is the spec's own
    `effort.argv` with `{effort}` substituted and each element shell-quoted, ready to splice into a
    launch line — and it is `''` unless the seat's declared word is ON that ladder.

    THAT LAST BOUND IS A SAFETY PROPERTY, not tidiness: an invalid `--variant` is SILENTLY ACCEPTED
    by opencode (exit 0, no warning — measured 2026-08-11), so an unvalidated word must never reach
    a binary. `validate_seat` refuses the off-ladder word one guard earlier; this returns nothing
    for it, so neither door can emit one."""
    try:
        tool = Path(__file__).resolve().parents[1] / "operator" / "bindings" / "tool"
        if str(tool) not in sys.path:
            sys.path.append(str(tool))
        from bindings import DEFAULT_PROFILES
        path = str(DEFAULT_PROFILES)
        st = os.stat(path)
        stamp = (st.st_mtime_ns, st.st_size)
        harness = str(w.get("harness") or "")
        model = str(w.get("model") or "")
        block = ((_profiles_doc(path, stamp).get("launch-specs") or {}).get(harness) or {}).get(model)
        if isinstance(block, dict):
            rungs = _spec_rungs(harness, model, path, stamp)
            rungs = None if rungs is None else list(rungs)
            declared = str(w.get("effort") or "").strip()
            if not rungs or declared not in rungs:
                return rungs, ""
            frag = [str(el).replace("{effort}", declared)
                    for el in ((block.get("effort") or {}).get("argv") or [])]
            return rungs, " ".join(shlex.quote(el) for el in frag)
    except Exception:
        return None, ""
    return None, ""


def validate_seat(w):
    """Pre-flight launch validation — PROP-8 (tv-ux-review): an invalid model slug in one
    wave's briefings stalled the ENTIRE wave at model-init, after every pane had already
    spawned and before any seat reached its boot prompt. Validates only what the kit can know
    locally (accepted alias/slug SHAPES per harness) — never a provider call. A well-formed
    slug the provider still rejects dies at boot anyway; the watcher's leftover-window flag
    (PROP-10) is the detection net for that residue. Returns '' when launchable, else the
    reason (used to refuse a launch BEFORE any pane opens).

    ⚠ IT IS A TYPO-CATCHER, NEVER A SECURITY GATE, and it was owner-ruled NOT tightened when
    the claude branch's raw `model` interpolation was quoted (2026-08-12): codex has
    NO model rule here at all — any string, the empty one included, is accepted — so
    `shlex.quote` at the COMPOSITION SITE in `harness_command` is the only thing that has ever
    made those two branches safe, and is now the only thing making claude's safe. NEVER treat a
    slug this function accepted as sanitized. It is written HERE because `bindings.py#catalog`
    imports this very function as its catalog validator, so the misreading is one import away.
    """
    if w["harness"] not in HARNESSES:
        return f"unknown harness '{w['harness']}' (expected one of {', '.join(HARNESSES)})"
    if w["harness"] == "claude" and not (
            w["model"] in CLAUDE_MODEL_ALIASES or w["model"].startswith("claude-")):
        return (f"claude model '{w['model']}' is neither a known alias "
                f"({', '.join(CLAUDE_MODEL_ALIASES)}) nor a full claude-* model id — "
                f"write a genuinely new alias as its full claude-* id")
    if w["harness"] == "opencode":
        if not w["model"]:
            return "opencode seats require an explicit model: (provider/model slug)"
        if not OPENCODE_MODEL_RE.fullmatch(w["model"]):
            return (f"opencode model '{w['model']}' is not a provider/model slug "
                    f"(e.g. deepseek/deepseek-v4-pro)")
    # THE EFFORT TERM. Until this existed a bad effort surfaced only when the real binary rejected
    # the composed line INSIDE AN ALREADY-OPENED PANE — or, on opencode, not at all (an invalid
    # `--variant` exits 0 and applies nothing). It is gated on the KEY being present, never on its
    # truthiness: `bindings.py#catalog` calls this with exactly {agent, harness, model} to ask the
    # harness+model question, and must keep getting that answer. A caller who omits the key
    # therefore gets NO effort validation rather than a refusal — the deliberate compatible shape,
    # and the reason this cannot be `if not w.get("effort")`, which would refuse that call site.
    if "effort" in w:
        rungs, _frag = _cast_effort(w)
        if rungs:  # `[]` (inert, G-270) and `None` (no dial / uncatalogued pair) both ACCEPT
            declared = str(w.get("effort") or "").strip()
            ladder = ", ".join(f"{i + 1}={r}" for i, r in enumerate(rungs))
            if not declared:
                return (f"effort-missing: seat '{w.get('agent')}' carries no 'effort' — the "
                        f"harness·model·effort triple is required, and {w['harness']}/{w['model']} "
                        f"runs on a profile with a real ladder ({ladder})")
            if declared not in rungs:
                return (f"effort '{declared}' is not a rung of the ladder "
                        f"{w['harness']}/{w['model']} runs on ({ladder}) — a seat stores the "
                        f"HARNESS'S OWN WORD, so a word from another harness's ladder, or one this "
                        f"ladder no longer carries, refuses HERE rather than reaching the binary")
    return ""


def prompt_file(args, agent, prompt):
    """Write a seat's boot prompt to a file under the package and return its path.

    EVERY harness command reads its prompt from a file rather than carrying it inline: the start
    line is typed into the pane as literal keystrokes, and a prompt with newlines is executed line
    by line by the pane's shell (G-11 — see wake()). A file keeps the start line one line no matter
    how long the prompt grows, so launch and close share one path with one failure mode."""
    d = base_dir(args) / "prompts"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{agent}-{file_stamp()}.txt"
    p.write_text(prompt, encoding="utf-8")
    return p


def harness_command(w, prompt=None, prompt_path=None):
    """The shell command that starts this seat's session, or (None, reason). Carries the seat's
    identity as an env prefix (see identity_prefix). Pass `prompt_path` (what every real spawn
    does, via prompt_file) to read the prompt from a file; `prompt` inlines it and is for dry-run
    display only — an inlined multi-line prompt is exactly the G-11 defect."""
    env = identity_prefix(w["agent"])
    if prompt_path is not None:
        arg = '"$(cat ' + shlex.quote(str(prompt_path)) + ')"'
    else:
        arg = shlex.quote(prompt or "")
    # The seat's effort, spelled the way ITS OWN PROFILE spells it — see `_cast_effort`. Empty for
    # an inert dial, for a pair no profile in this workspace casts, and for a word off the ladder
    # (which `validate_seat` refuses one guard earlier). Already shell-quoted element by element,
    # which is what closes the raw f-string interpolation the claude line used to carry.
    eff = _cast_effort(w)[1]
    eff = f" {eff}" if eff else ""
    if w["harness"] == "claude":
        return f"{env}{CLAUDE_BIN} --model {shlex.quote(w['model'])}{eff} {arg}", ""
    if w["harness"] == "codex":
        model = f" -m {shlex.quote(w['model'])}" if w["model"] else ""
        # 7.612 / `d-codex-hook-trust-bypass` (2026-08-09): codex trust-gates hooks BY HASH,
        # and a seat folder's hooks.json is DERIVED — regenerated on every re-materialize —
        # so persisted trust re-breaks and the seat boots with its hooks SKIPPED, pending an
        # interactive `/hooks` review no agent performs. The daemon half of the ruling already
        # carries it (envelope/spawn-profiles.yaml, `codex-gpt-5-5`); this is the kit half.
        # ⚠ SCOPE GUARD, CHECKED NOT ASSUMED: `harness_command` and `resume_command` are the
        # only two codex compositions in this file, and BOTH build agent-seat commands. The
        # flag rides agent seats ONLY — if a human-interactive codex composition is ever added
        # here, it stays clean.
        return f"{env}{CODEX_BIN} --dangerously-bypass-hook-trust{model}{eff} {arg}", ""
    if w["harness"] == "opencode":
        if not w["model"]:
            return None, "opencode seats require an explicit model: (provider/model slug)"
        # G-13: the kit built `opencode --model X --prompt Y`. This opencode has NEITHER flag at
        # top level — the one-shot form is the `run` SUBCOMMAND (`opencode run -m <slug> <msg>`,
        # verified live on deepseek and glm-5.2). The old string fell through to the TUI and the
        # prompt was never run: a launch command nobody had executed end to end. NOTE the shape
        # this imposes — `run` is ONE-SHOT: an opencode seat executes its prompt and exits, so it
        # cannot be woken later; it must read its own messages before finishing, and a wake aimed
        # at its pane after that would type into a bare shell (the harness-up guard refuses it).
        # OWNER-DIRECTED (2026-07-27, owner present; leader #607): seats initiate with auto mode
        # ON. Without it EVERY opencode seat runs with permissions live, auto-REJECTS reads outside
        # its own folder and dies silently — it is what killed K4 three times and it is G-49's
        # mechanism for the whole opencode half of the roster.
        #
        # POSITION IS LOAD-BEARING AND IS G-13 ALL OVER AGAIN. `--auto` must come AFTER the `run`
        # subcommand. Verified live by two of us independently, not read off the help:
        #   `opencode --auto run -m X P`  -> PRINTS THE BANNER AND RUNS NOTHING, exit 0
        #   `opencode run --auto -m X P`  -> returns the expected string
        # The wrong form is the dangerous one precisely because it exits 0: it would look like a
        # fix, pass any check that only asserts the flag is present, and launch nothing.
        return f"{env}{OPENCODE_BIN} run --auto -m {shlex.quote(w['model'])}{eff} {arg}", ""
    return None, f"unknown harness '{w['harness']}' (expected one of {', '.join(HARNESSES)})"


def ask_body(row):
    """The ask's words, read off the row's `evidence_pointer`, or `''`.

    §3 keeps the BODY out of the store and defines `evidence_pointer` as the thread permalink or an
    on-disk copy; `server/heart/ask-record.js` writes that copy when the daemon stamps the row. An
    unreadable pointer yields no words rather than an error — a body that cannot be read must not
    turn into an ask that cannot be seen, nor into a raised exception on a boot path."""
    try:
        return Path(row.get("evidence_pointer") or "").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def unanswered_ask_block(pkg):
    """Every still-open owner ask for `goal-master`'s NEXT sitting, or `''`.

    READ-ONLY, and deliberately so: `ignite/bridges/chat/ask-store.js` is the ONE WRITER of the
    `open_asks` rows (spec-state-store §3) — it inserts on an inbound owner message to a goal
    channel and reaps at the ONE place every owner-facing post passes through. A second writer here
    would be the cross-process write-ownership problem the ONE store exists to end.

    ⚠ `owner-asks.json` IS GONE. The per-goal JSON file this used to parse was a second record of
    the same fact, so both shapes it once had to normalize (the D89-Q4 list and the pre-D89 bare
    entry) are gone with it. `ask_id` is the Slack thread [T5-R7]; the ask body is read back off
    `evidence_pointer`, which §3 defines as the thread permalink or the on-disk reply copy.

    `list_open_asks` IS §2.1's own WHERE clause (`state='open' AND posted=1`) — the same two facts
    a seat's derived wait is made of, asked once rather than re-filtered here, so this view and the
    scheduler's can never disagree about which asks are open.

    NEVER RAISES. `boot_prompt` composes on EVERY relaunch of EVERY seat (`cmd_boot_prompt`'s own
    docstring); an unreadable or absent store must degrade to an absent ask, not a boot prompt that
    never composes — that would break every seat's launch, not just goal-master's.

    Checked AT FIRE TIME against the SAME rows the bridge reaps, so a re-inject racing a
    just-delivered answer sees the reap the moment it lands, not a snapshot taken when the ask was
    first made.
    """
    open_asks = []
    try:
        rows = ending_store.list_open_asks(pkg, seat="goal-master")
    except Exception:                                  # noqa: BLE001 — see NEVER RAISES above
        return ""
    for row in rows:
        text = ask_body(row)
        if not text:
            continue
        open_asks.append((str(row.get("posted_at") or "an earlier sitting"), text))
    if not open_asks:
        return ""
    if len(open_asks) == 1:
        asked_at, text = open_asks[0]
        return (
            f"\n\n⚠ AN UNANSWERED OWNER ASK IS STILL OPEN (asked {asked_at}) — no reply has "
            f"been recorded on it since. Answer it before anything else this sitting:\n\n{text}\n")
    numbered = "\n\n".join(
        f"{i}. (asked {asked_at}) {text}" for i, (asked_at, text) in enumerate(open_asks, 1))
    return (
        f"\n\n⚠ {len(open_asks)} UNANSWERED OWNER ASKS ARE STILL OPEN — no reply has "
        f"been recorded on any of them since. Answer them before anything else this sitting, "
        f"oldest first:\n\n{numbered}\n")


def boot_prompt(w, args, daemon_lane=False):
    """The initial prompt every seat starts with, harness-independent. A leader seat whose
    memory.md already exists is only ever (re)launched to CONTINUE a run it was arbitrating
    (renew, or crash recovery) — its prompt is resume-first, never the generic fresh boot."""
    pkg = package_dir(args)
    wdir = workers_dir(args)
    mem = (w["folder"] / "memory.md") if w["folder"] else None
    if w["agent"] == "leader" and mem and mem.exists():
        first = (f"You are RESUMING a prior session, not starting fresh: read {mem} FIRST — "
                 f"especially its 'Resume here' section — it is your own state from the session "
                 f"this relaunch continues; do not re-run work it records as complete. "
                 f"Then read your briefing {w['briefing']}.")
    else:
        memory = ""
        # G-23: a `close: mechanical` seat is memoryless BY DESIGN — it must not be told to read a
        # memory.md, or it would trust a file its close path never writes and that goes stale the
        # moment its external state moves. Long-lived, but boots fresh every session.
        if w["folder"] and not w["ephemeral"] and not w.get("mechanical_close"):
            memory = (f" If {mem} exists, read it too — it is your PREDECESSOR'S HANDOFF for you "
                      f"(protocol item 9); trust it as your own notes, and after reading it the "
                      f"file is YOURS: a present-tense state doc you REWRITE in place at your own "
                      f"renewal/close — resolved items deleted, ≤2 screens, never a log.")
        first = f"Read your briefing {w['briefing']} first.{memory}"
    # ⚠ F1 (owner ruling, 2026-08-17) — BOTH LANES CHECK IN. The daemon lane's opening differs in
    # ONE sentence: its check-in is paneless.
    #
    # W1 dropped the check-in instruction on this lane because `checkin` had no identity to
    # register a paneless seat under. That was measured wrong at its consequence, not its premise:
    # the ACTIVE roster row `checkin` writes is what `checkout` gates on, what `persist_cursor`
    # writes through, what makes `ready-seats` report RUNNING, and what gives `send`/`close-seat` a
    # handle. Dropping it did not cost one instruction — it cost the seat its ending (30 of 45 rows
    # attested `exited`/`kit` because no seat could declare its own), its cursor (~49 messages
    # re-read per leader sitting), and the RUNNING mutex (twin leader sittings 4 s apart).
    #
    # The W1 comment that stood here also promised "check-out WORKS on this lane". It did not, and
    # could not: `cmd_checkout` refuses at its roster gate BEFORE any write, and `--force` is not
    # read on that refusal. It works now because the row exists.
    #
    # ⚠ THE PROTOCOL IS NAMED FROM THE KIT, NOT FROM THE PACKAGE — and both lanes name the SAME
    # bytes, because they are composed once, here, and concatenated by both branches below. Until
    # 2026-08-15 both lanes said "read {pkg}/CLAUDE.md and follow its coordination protocol
    # exactly". That file is a deterministic ROUTER (owner ruling R21): a file table and the
    # write-if-something ledgers, 1976 bytes, and NOT ONE LINE of coordination protocol. So every
    # seat on every lane was sent for instructions that are not there, at the one moment it is
    # deciding how to behave. `protocol.md` is the protocol — it is already what "protocol item 9"
    # in the memory sentence above resolves in.
    #
    # ⚠ F7 (owner ruling, 2026-08-17) ABOLISHED `conduct.md`. The four procedures that file
    # carried (check in, declare outcome, check out, file issues) live ONCE in this composer —
    # no second template, no per-seat snippet, no leftover "read conduct.md" line. Model policy
    # does not survive here: nothing enforced it.
    #
    # ⚠ IT IS INSIDE THE CAGE. `envelope/spawn-profiles.yaml`'s `cage.SeatBinds` opens
    # `ro-bind:{grant:readRoot}` — the whole workspace root, read-only, FIRST in the stack — and
    # the kit lives under it. `cage.js#composeAncestorMasks` cuts only `CLAUDE.md`/`AGENTS.md` and
    # the harness config dirs, and only on the walk-up from the seat's launch folder, which the kit
    # is not on. Verified through `cagespec.py#evaluate` for a live flagship seat.
    kit = Path(__file__).resolve().parent
    reads = (
        f"Then read {kit / 'protocol.md'} — THE coordination protocol, messaging, identity and "
        f"lifecycle mechanics — and follow it exactly. ({pkg}/CLAUDE.md is your goal's "
        f"ROUTER — where things are and where to write — and carries no protocol; read it for "
        f"that.) ")
    if daemon_lane:
        opening = (
            reads +
            f"Then check in as '{w['agent']}' (coordination CLI: {coord_invocation(args)}) — the "
            f"SAME protocol as every other lane, with ONE amendment: your check-in is PANELESS. "
            f"You have no tmux pane, so it registers you against the still-open session row already "
            f"opened for you in {pkg}/sessions.csv, and it says so on its own output. That roster "
            f"row is what makes your CHECK-OUT work, what lets others address and close you, and "
            f"what keeps your read cursor — so check in FIRST, before anything else. Because you "
            f"hold no pane, no wake can reach you: run `read` at your own checkpoints. "
            f"Your check-out may report that it could not stamp {pkg}/sessions.csv — the run "
            f"package is mounted read-only in your cage on purpose; your declaration is recorded on "
            f"the writable surface and the daemon copies it across when your process ends. ")
    else:
        opening = (
            reads +
            f"Then check in as '{w['agent']}' (coordination CLI: {coord_invocation(args)}). ")
    procedures = (
        f"A sitting ends by declaring `done` or `incomplete`; process exit is not a declaration. "
        f"CHECK OUT when you end — `checkout --incomplete \"<reason>\"` is the ONLY way to end a "
        f"session honestly unfinished; a plain `checkout` says your briefing's output exists. "
        f"File issues as appends to {pkg}/issues.md with id `G-<seat>-<MMDD>-<HHMM>`. "
        f"Then execute ONLY your briefing. ")
    # ── W3 · THE ROUTED-FAIL PAYLOAD, folded in HERE and nowhere else ─────────────────────────
    #
    # A relaunch grant on its own re-runs the seat on its STALE SEED — which is precisely how D6's
    # false-complete was manufactured: the seat ran again, saw the same inputs, and reported the
    # same finish. The payload is what makes the second sitting DIFFERENT from the first, and this
    # is the one composer every launcher on every lane goes through, so folding it in here reaches
    # the daemon's seeding pass and `launch` alike with no second reader.
    #
    # ⚠ IT IS APPENDED, NEVER SUBSTITUTED. The seat still reads its briefing and still follows the
    # protocol; the payload says why THIS sitting exists. A payload that replaced the prompt would
    # hand a relaunched seat no idea what it is.
    payload = read_route_payload(base_dir(args, register=False), w["agent"])
    routed = ("\n\n⚠ THIS SITTING WAS ROUTED TO YOU — read this before your briefing's ordinary "
              "work; it is the reason you were relaunched and it is NOT in the inputs you ran on "
              f"last time:\n\n{payload}\n") if payload else ""
    # D57/D75 — SCOPED BY AN EXPLICIT NAME CHECK, never a filter that happens to match today. This
    # composer serves EVERY seat's EVERY relaunch; only `goal-master` may ever carry an owner-ask
    # ferry record, so every other seat's boot prompt is provably byte-unchanged by this addition.
    ask_block = unanswered_ask_block(pkg) if w["agent"] == "goal-master" else ""
    return (
        f"You are agent '{w['agent']}' of the run package at {pkg}. "
        f"{first} "
        f"{opening}"
        f"{procedures}"
        f"{scratchpad_instruction(w, daemon_lane)}"
        f"Never read any other agent's briefing or folder in {wdir}/. "
        f"Message 'leader' on any conflict, inconsistency, or decision you cannot settle alone."
        f"{routed}"
        f"{ask_block}"
    )


def scratchpad_instruction(w, daemon_lane=False):
    """The seat-facing per-session scratchpad instruction (7.96 criterion 3), or `''`.

    ⚠ W1 (adv, C4) — THE SESSION-ID'S SOURCE MOVES WITH THE LANE. This sentence used to promise
    that the id "is printed to you by your own check-in", which is true on the tmux lane and a
    dangling promise on the daemon lane the moment the check-in instruction is dropped above. The
    daemon lane's seat reads it off its own OPEN row in the package's `sessions.csv` — a file its
    cage mounts read-only, so it can always be read and never forged. It is the same id either way.

    ⚠ THE BOOT PROMPT IS THE ONE HOME, and the criterion says one home and not both. The
    alternative was the run package's `CLAUDE.md` — which `materialize-seats.py` authors per
    package, so the instruction would reach only packages created after the change and would be
    absent from every existing one. This surface is composed by the kit on EVERY boot, so a seat
    launched into a package written last month is instructed exactly like one launched into a
    package written today. The check-in's identity line REPORTS the resolved path; it does not
    repeat the instruction.

    ⚠ IT NAMES WHAT STAYS AT THE ROOT, and that half is not decoration: KG `seat-folder` box 1
    homes the descriptor, the memory and the conventions at the seat-folder ROOT, so an instruction
    that said only "working files go in the scratchpad" would leave a seat to guess about the three
    files it actually opens — and a guess either way mints a SECOND home for one file class, which
    is the failure this sentence exists to prevent.

    Empty for a seat whose folder could not be resolved: naming a path under a folder that does not
    exist is worse than saying nothing, because the seat would create it somewhere of its own
    choosing."""
    if not w.get("folder"):
        return ""
    where = ("the `session-id` cell of YOUR row in the package's `sessions.csv` — the one whose "
             "`ended` cell is still empty; create the folder if it is not there"
             if daemon_lane else
             "printed to you by your own check-in, on its `session:` line, and the folder "
             "already exists")
    return (f"EVERY working file you produce this session goes in your per-session scratchpad "
            f"{Path(w['folder']) / SEAT_SCRATCHPAD_DIR}/<session-id>/ — <session-id> is {where}. "
            f"Your seat.md/agent.md descriptor, your memory.md and any conventions.md STAY at "
            f"{w['folder']}/ — nothing already at that root moves into the scratchpad. ")


def cmd_boot_prompt(args):
    """Print ONE seat's boot prompt — the exact bytes `launch` writes to that seat's prompt file.

    THE ONE COMPOSER, REACHED FROM OUTSIDE. `boot_prompt` above is what `launch_seat` boots every
    seat on, and it is the only place that knows the ephemeral/persistent split, the memory-file
    instruction, the leader's resume-first form and the scratchpad sentence. A LAUNCHER THAT IS NOT
    `launch` — the daemon's seeding pass, `supervisor/seeding.js` — needs those same bytes, and until
    this verb existed it had no way to ask for them: its queue row carried `{profile, workdir}` and
    no `prompt` at all, so the spawn path wrote a 0-BYTE prompt file and the harness exited 1 on
    "Input must be provided either through stdin or as a prompt argument when using --print"
    (measured on two goals, 2026-08-11, execs 26274 and 26358). Composing the prompt a second time
    in JavaScript would be the drift PRIN-11 exists to prevent, so the launcher asks THIS one.

    A SEAT WITH NO DESCRIPTOR IS REFUSED BY NAME, never answered with an empty prompt — an empty
    prompt IS the defect above, and printing one here would only move it.

    READ-ONLY ON THE PACKAGE: writes no prompt file, opens no pane, messages nobody, wakes
    nobody. It resolves the package like every other command, which (re-)registers the run tag
    in ~/.config/rbtv — the same idempotent best-effort write `launch` itself makes."""
    wdir = workers_dir(args, register=False)
    seats = discover_workers(wdir)
    w = next((x for x in seats if x["agent"] == args.seat), None)
    if w is None:
        pkg_bp = package_dir(args, register=False)
        if args.seat not in registered_seats(pkg_bp):
            refuse("input",
                   f"'{args.seat}' is not a registered seat (no row in taskforce.csv or "
                   f"sessions.csv), so there is nothing to compose a boot prompt FROM.\n"
                   f"Registered seats: {', '.join(sorted(registered_seats(pkg_bp))) or '(none)'}",
                   2)
        refuse("input",
               f"'{args.seat}' has no descriptor under {wdir}, so there is nothing to compose a "
               f"boot prompt FROM — and an empty prompt boots a harness that exits on empty "
               f"input. Seats with a descriptor here: "
               f"{', '.join(sorted(x['agent'] for x in seats)) or '(none)'}\n"
               f"Materialize the taskforce first: python3 "
               f"{Path(__file__).resolve().parent / 'materialize-seats.py'} --package "
               f"{package_dir(args, register=False)}",
               2)
    # ⚠ W1 (adv, C4) — THE LANE IS TOLD, NEVER DERIVED HERE. `execution-lane`'s grammar already
    # has exactly two spellings that DEC-1 binds to change together (`supervisor/lane-watch.js#readLane`
    # and `goals-tree/tool/goal_cli.py#read_lane`); a third one in this file would be a third thing
    # to keep in step for a one-bit answer the CALLER already holds. `seeding.js` reads the marker
    # through the existing JS speller and passes the result. Absent flag = the tmux lane = the
    # bytes this verb has always printed.
    sys.stdout.write(boot_prompt(w, args, daemon_lane=(getattr(args, "lane", "") == "daemon")))


# ---------- worker-mirror refresh (pre-launch) ----------
# A codex/opencode seat reads its rules from the AGENTS.md + .agents/ MIRROR of the launch root's
# CLAUDE.md/skills/rules — not from the sources themselves. The mirror only refreshes when the
# installer runs, and every AGENTS.md is gitignored, so drift is invisible to git and per-machine:
# a skill edited an hour ago reaches a claude seat and NOT the codex seat beside it. Nothing else
# consumes the mirror, so launch IS the moment it must be current — refresh at the point of
# consumption rather than on a clock.

MIRROR_REFRESH_TIMEOUT = 300  # a cold full-workspace render; the steady-state run is ~2-3s


def find_workspace_root(start):
    """Walk up from `start` for the workspace root carrying rbtv.json.

    Returns (root, rbtv_path_abs) — (None, None) when no rbtv.json is found (not an rbtv
    workspace), (root, None) when one exists but names no readable rbtv_path.
    """
    try:
        p = Path(start).resolve()
    except OSError:
        return None, None
    for d in (p, *p.parents):
        cfg = d / "rbtv.json"
        if not cfg.is_file():
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return d, None
        rel = data.get("rbtv_path")
        if not rel:
            return d, None
        # rbtv_path is recorded workspace-relative; an absolute value is honoured as-is.
        return d, (Path(rel) if Path(rel).is_absolute() else (d / rel)).resolve()
    return None, None


def refresh_mirror(cwd):
    """Refresh the worker mirror for the workspace owning `cwd`.

    Returns (status, detail) where status is:
      "ok"   — the mirror was refreshed (detail = the installer's summary line)
      "skip" — nothing to refresh (detail says why): not an rbtv workspace, or one with no
               mirror installed. NOT an error: a workspace without elected CLI workers has
               no mirror by design.
      "fail" — the refresh was attempted and failed (detail = the reason)
    """
    root, rbtv_path = find_workspace_root(cwd)
    if root is None:
        return "skip", f"no rbtv.json at or above {cwd} — not an rbtv workspace"
    if rbtv_path is None:
        return "fail", f"{root / 'rbtv.json'} is unreadable or names no rbtv_path"

    installer = rbtv_path / "install.py"
    if not installer.is_file():
        return "fail", f"installer not found at {installer} (rbtv_path points nowhere)"

    # --exclude is deliberately OMITTED: the driver defaults excluded_paths from the recorded
    # state, so omitting it PRESERVES the workspace's exclusions. Passing it here would replace
    # them and start rendering mirrors into paths the owner excluded.
    cmd = [sys.executable, str(installer), "--mirror", "--non-interactive", "--target", str(root)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=MIRROR_REFRESH_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "fail", f"refresh timed out after {MIRROR_REFRESH_TIMEOUT}s"
    except OSError as exc:
        return "fail", f"could not run the installer: {exc}"

    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip().splitlines()
        return "fail", (err[-1] if err else f"installer exited {r.returncode}")

    summary = next(
        (ln.strip() for ln in reversed((r.stdout or "").splitlines()) if "Mirror:" in ln),
        "mirror refreshed",
    )
    if "no mirrorable packages elected" in summary:
        return "skip", "workspace elects no mirrorable CLI workers — no mirror to refresh"
    return "ok", summary


def refresh_mirrors_for(workers):
    """Refresh the mirror for every distinct launch root among the NON-claude seats.

    Claude seats read CLAUDE.md natively and consume no mirror, so a claude-only launch does no
    work here. Deduped by root: an N-seat wave rooted in one workspace pays one refresh, and a
    seat rooted in a worktree gets ITS root refreshed rather than the parent's.

    NEVER blocks the launch. A failed refresh is reported loudly and the seats still boot — a
    broken installer must not be able to stop a team run, and a stale mirror still carries the
    previous render's rules rather than none.
    """
    roots = list(dict.fromkeys(
        w["cwd"] for w in workers if w["harness"] != "claude" and w["cwd"]
    ))
    for cwd in roots:
        status, detail = refresh_mirror(cwd)
        if status == "ok":
            print(f"mirror refreshed for {cwd}: {detail}")
        elif status == "skip":
            print(c(f"mirror: skipped for {cwd} — {detail}", C_HINT))
        else:
            print(c(f"WARNING mirror refresh FAILED for {cwd} — {detail}", C_DEAD), file=sys.stderr)
            print(c("  the codex/opencode seats below may read STALE rules; refresh by hand with "
                    "`python install.py --mirror --non-interactive --target <root>`", C_DEAD),
                  file=sys.stderr)


def seat_placement(w):
    """Pure placement decision from the briefing's window: value — ("own", agent-name) for
    `yes`, ("shared", NAME) for a named wave window, ("pane", None) otherwise."""
    if w["window"] == "yes":
        return "own", w["agent"]
    if w["window"]:
        return "shared", w["window"]
    return "pane", None


def launch_seat(w, args, target, prompt=None, pane=None, resume=None, strict_liveness=False):
    """Open a pane/window for one seat and start its harness. Returns (pane_id, err).

    `strict_liveness` (7.567) decides what happens on the THIRD outcome — this host could not
    observe the harness either way. `cmd_launch` sets it, because the ruling that `exit 0` means
    POSITIVELY OBSERVED is about the launch verb's exit code. The renew/relaunch/restart callers
    leave it off and keep their pre-7.567 behaviour: an indeterminate verdict is warned about and
    passed, because their failure paths kill panes, fire lifecycle alarms and re-launch seats — a
    false failure there costs more than an unverified success, the same asymmetry the checkin path
    already rules on.

    `pane` reuses an EXISTING pane (a renew respawned in place — G-12) instead of placing a new
    one. Never returns success on a pane where no harness came up: G-11's whole failure was a
    start line that the pane's shell swallowed while the roster went on believing the seat live.

    `resume` is a `sessions_resume_ref` ref (7.32 leaf (ii)): the harness re-enters that recorded
    conversation instead of booting fresh. EVERYTHING ELSE on this path is unchanged — the pane,
    the placement, the statusline, the harness-up wait and the new sessions.csv row are the same
    acts, so a resumed seat is observed exactly like a booted one. A resumed session is still a NEW
    session of the seat and gets its own row: the process is new even though the conversation is
    not, and the row is what the NEXT crash resumes from."""
    verr = validate_seat(w)  # PROP-8: `close-seat --renew` relaunches single seats through here
    if verr:
        return "", verr
    # 7.400: created HERE, not inside identity_prefix — this is the one door every boot passes
    # (`launch` and `close-seat --renew` both arrive here), so the dir exists before the harness
    # command that names it ever runs. `exist_ok=True`: a seat launched moments earlier already
    # made it, and that is not an error.
    os.makedirs(AGENT_TMPDIR, mode=0o700, exist_ok=True)
    os.chmod(AGENT_TMPDIR, 0o700)
    # Checked HERE because this is the one door every boot passes — `launch` and
    # `close-seat --renew` both arrive here, so a renew cannot drift where a launch is checked.
    # Peers are read from ALL briefings, not from the seats in this wave: a single-seat renew would
    # otherwise have no peers to compare against and skip the check exactly when it matters.
    if not getattr(args, "force", False):
        derr = window_drift(w, peer_windows(discover_workers(workers_dir(args)), w["agent"]))
        if derr:
            return "", derr
    ppath = prompt_file(args, w["agent"], prompt or boot_prompt(w, args))
    if resume:
        cmd, err = resume_command(w, resume, ppath)
    else:
        cmd, err = harness_command(w, prompt_path=ppath)
    if cmd is None:
        return "", err
    if pane:
        place = "existing"
    else:
        place, wname = seat_placement(w)
        if place == "own":
            pane, err = tmux_new_window(target, wname, w["cwd"])
        elif place == "shared":
            existing = tmux_find_window_pane(tmux_session_name(target), wname)
            if existing:
                pane, err = tmux_split_pane(existing, w["cwd"])
            else:
                pane, err = tmux_new_window(target, wname, w["cwd"])
        else:
            pane, err = tmux_split_pane(target, w["cwd"])
        if not pane:
            return "", err
    set_pane_title(pane, w["agent"])
    # 7.31: TRANSCRIPT CAPTURE IS ARMED HERE — in the step that composes the pane command, at pane
    # BIRTH, before the harness is woken — and never at close: tmux scrollback dies with the tmux
    # server, so a close-time capture returns nothing exactly when the substrate-level backup
    # matters. The session-id is minted before the row because the transcript path CARRIES it
    # (R31); the ROW still waits for `wait_harness_up`, so nothing here weakens 7.37's rule that a
    # session row means a seat that provably booted. A renew respawning into an existing pane
    # re-points the pipe at its own new session folder, which is why this sits after the `pane`
    # branch and not inside it.
    sid31, rec31 = "", ""
    try:
        pkg31 = package_dir(args)
        sid31 = mint_session_id(pkg31, w["agent"])
        tpath31 = session_transcript_path(pkg31, w["agent"], sid31)
        started31, cerr31 = start_pane_capture(pane, tpath31)
        rec31 = str(tpath31) if started31 else ""
        if not started31:
            print(c(f"WARNING {w['agent']}: pane transcript capture did NOT arm — {cerr31}. The "
                    f"seat is fine and its harness-native transcript is unaffected; the "
                    f"substrate-level backup is NOT being written, and `recorded` stays blank "
                    f"rather than naming a file nothing writes.", C_DEAD), file=sys.stderr)
    except Exception as exc:                                   # noqa: BLE001 — deliberate
        # Same trade-off `session_trace_safe` makes one act later: bookkeeping ABOUT the boot must
        # never become a gate ON it. Loud, and swallowed.
        print(c(f"WARNING {w['agent']}: pane transcript capture could not be armed — "
                f"{type(exc).__name__}: {exc}", C_DEAD), file=sys.stderr)
        sid31, rec31 = "", ""
    write_seat_statusline(w)   # 7.69: before the harness reads its settings, never after
    since = time.time()        # 7.37: the instant the transcript must post-date (renew-correct)
    ok, terr = wake(pane, cmd)
    if not ok:
        return pane, f"pane opened but harness start FAILED: {terr}"
    _, uerr = wait_harness_up(pane)
    if uerr.startswith(HARNESS_UP_UNVERIFIABLE) and not strict_liveness:
        print(c(f"WARNING {w['agent']}: {uerr}. Proceeding as if it booted (see "
                f"`strict_liveness`).", C_DEAD), file=sys.stderr)
        uerr = ""
    if uerr:
        return pane, uerr
    if w["harness"] == "claude":
        schedule_session_rename(pane, w["agent"])
    # 7.37: the session row is written by the RUN, here, on the one path every seat boot takes —
    # `launch` and `close-seat --renew` both arrive here. A renew is a NEW session of the same
    # seat, which is exactly the "one seat, several sessions within one run" the KG names.
    # Only AFTER the harness is verified up: a row for a seat that never booted is the G-11 lie
    # in a second file.
    res, terr2 = session_trace_safe(session_open, args, w, since=since, pane=pane,
                                    session_id=sid31 or None, recorded=rec31)
    if terr2:
        print(c(f"WARNING {w['agent']}: the seat IS UP but its sessions.csv row was NOT written "
                f"— {terr2}. The trace is incomplete; the seat is fine.", C_DEAD), file=sys.stderr)
    elif res and res[1]:
        print(c(f"  {w['agent']}: session {res[0]} — {res[1]}", C_HINT))
    return pane, ""


def seats_by_name(args, names=None):
    workers = discover_workers(workers_dir(args))
    if names is None:
        # A bare `launch` (no --only) never boots leader — the owner starts leader by hand;
        # only an explicit by-name launch or a close-seat --renew may target the leader seat.
        return [w for w in workers if w["agent"] != "leader"]
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    picked = [w for w in workers if w["agent"] in wanted]
    have = {w["agent"] for w in picked}
    registered = registered_seats(package_dir(args))
    missing = set(wanted) - have - registered
    if missing:
        known = ", ".join(sorted(registered | have)) or "(none)"
        refuse(
            "state",
            f"no register carries seat `{', '.join(sorted(missing))}` "
            f"(taskforce.csv ∪ sessions.csv), so there is nothing to launch under that name.\n"
            f"registered seats: {known}\nFix the name, or add a taskforce.csv / sessions.csv row "
            f"first.",
            1)
    bindings = taskforce_bindings(args)
    for name in wanted:
        if name in have:
            continue
        row = bindings.get(name) or {}
        picked.append({
            "agent": name,
            "briefing": None,
            "harness": (row.get("harness") or "").strip(),
            "agent_type": "",
            "model": (row.get("model") or "").strip(),
            "effort": (row.get("effort") or "").strip(),
            "cwd": VAULT_ROOT,
            "window": "",
            "ephemeral": False,
            "ctx_refresh": None,
            "mode": "",
            "folder": None,
            "mechanical_close": False,
            "outputs": [],
            "outputs_declared": False,
            "outputs_defect": False,
        })
        have.add(name)
    return picked


# ---------- 7.278 (C3): THE CAPACITY TERM'S LITERAL LINES ---------------------------------------
#
# Carried VERBATIM from `capacity-admission-spec.md` §6.1 and §6.2 — the spec prints these, this
# file does not paraphrase them. They are module-level so a selftest row can assert the SHAPE
# without re-typing it, which is how a "the line is right" check stops being a check that the line
# equals itself.
#
# ⚠ NO POLICY NUMBER APPEARS IN EITHER STRING. Both numbers in the stamp form come from the
# census's own emitted fields AT RUNTIME (`snapshot_age_s`, `stale_after_s`) and the cap is named
# by FIELD NAME (`cap.agent_panes`), never by value: `r-floor-single-source` refuses a copy, and a
# threshold written into source would be that copy.
CAPACITY_DEGRADE_LINE = ("  capacity: CAP NOT CONSULTED — {reason} | admitted {n} seat(s) on the "
                         "memory floor alone (budget.json floors.launch_refuse_mb, read live at "
                         "the launch gate) | {stamp}")
CAPACITY_DEFER_LINE = ("  {agent}: DEFERRED (capacity) — cap.agent_panes headroom is exhausted for "
                       "this act; {k} of {m} counted candidate(s) admitted. This is a WAIT: the "
                       "pickup lane is A4's (deferred-pickup-lane.md).")
# §5.1 — the fact the EXIT CODE no longer carries, so the output must. A capacity deferral that
# empties the set exits 0: it is a WAIT, and a non-zero code would make a wait indistinguishable
# from a denial. This is the ONE place that says so.
CAPACITY_EMPTY_LINE = ("  capacity: NO PANE WAS OPENED — every counted candidate was "
                       "capacity-deferred. This is a WAIT, not a refusal: headroom on "
                       "cap.agent_panes returns as seats depart. No override flag carries this "
                       "term, and none may be attached to --force or --force-memory.")
# ---------- 7.363 (F19): THE CENSUS-FAILURE LINES — G-m4-demo-clause1-driver-0803-2335 ----------
#
# 7.278 wrote ONE degrade branch for every bad reading, on the rule that a SENSOR outage must not
# become a LAUNCH outage. G-2335 measured what that costs: a run whose sensor never starts loses
# the pane-cap half of its capacity term entirely and keeps launching on the memory floor alone,
# so the one term that bounds pane count stops binding the moment the sensor does — and says so as
# one line among twenty in a launch that otherwise reports success.
#
# 7.363 splits the branch. Where the census is merely IMPERFECT (D4 incomplete, D5 an in-run
# `cross_goal` row) it still produced a number, and 7.278's degrade stands unchanged. Where the
# census is ABSENT or STALE the room cannot count itself at all, and a counted pane is admitted
# BLIND — that case now DEFERS. It is still not a refusal: exit stays 0, the act names every
# deferred seat, and it names the PICKUP LANE in the same output, which is the clause that makes
# the enforcement recoverable rather than a launch outage by another name.
#
# ⚠ NO POLICY NUMBER APPEARS IN EITHER STRING, for the same reason as above: the cap is named by
# FIELD (`cap.agent_panes`) and never by value, and `{pkg}` is the caller's own package path.
CAPACITY_UNENFORCEABLE_LINE = (
    "  capacity: CAP UNENFORCEABLE — {reason} | cap.agent_panes cannot be checked at all, so NO "
    "counted candidate is admitted on the memory floor alone | {stamp}\n"
    "  capacity: this is a WAIT, not a refusal — the act exits ZERO. PICKUP LANE: the census sensor "
    "is retired and no replacement is built yet, so this state persists until one lands; the "
    "cadence sweep re-admits every deferred seat with no further act once it does "
    "(deferred-pickup-lane.md). No override flag carries this term, and none may be attached to "
    "--force or --force-memory.")
CAPACITY_CENSUS_DEFER_LINE = (
    "  {agent}: DEFERRED (capacity) — cap.agent_panes headroom is UNKNOWN for this act: the census "
    "could not be read, and this act will not admit a counted seat blind. Pickup lane above.")
# §4.5 — readings worth SAYING that are not worth DEGRADING on. They print on the full-capacity
# branch only: each one describes how the cap reading was USED, and on the degrade branch it was
# not used at all, so printing them there would describe a consultation that did not happen.
CAPACITY_NOTE_UNACCOUNTED = ("  capacity: {k} unaccounted pane(s) are INSIDE in_use — the cap "
                             "reading is conservative, not wrong. An owner console and a leaked "
                             "pane are indistinguishable here (budget.py's own ruling); reported, "
                             "never flagged.")
CAPACITY_NOTE_CROSS_GOAL = ("  capacity: {k} cross_goal pane(s) resolve OUTSIDE this run — ruled "
                            "not to count against this run's cap. They still spend RAM, which "
                            "budget.json floors.launch_refuse_mb protects, not the cap.")
# 7.555 — the D5 CORRECTION's own disclosure. It prints on the full-capacity branch beside N1/N2
# because that is where the correction is USED; before 7.555 this reading printed on the DEGRADE
# branch instead, as a reason the cap went unconsulted. Same fact, opposite consequence, so it says
# which. ⚠ NO POLICY NUMBER: `{k}` is the census's own row count and the cap is named by FIELD.
CAPACITY_NOTE_IN_RUN = ("  capacity: {k} cross_goal pane(s) resolve INSIDE this run's own seats/ — "
                        "this run's OWN seat(s), harness live, not yet checked in. `census()` files "
                        "them cross_goal and leaves them OUT of in_use, so they are COUNTED here "
                        "and headroom is reduced by {k}. Before 7.555 this DEGRADED the act and "
                        "left the cap unconsulted instead, and that degrade never cleared while "
                        "the harness stayed live and silent.")
# ⚠ THE LINE ABOVE DELIBERATELY DOES NOT CONTAIN THE DEGRADE MARKER `CAP NOT CONSULTED`, and this
# is not style. That string is a WIRE MARKER several rows assert the ABSENCE of to prove the act
# took the full-capacity branch; a note that merely NARRATES the old behaviour using the marker
# makes every such row read its own commentary and go red on correct code. Measured here: the first
# draft of this note carried the phrase and reddened 7.555's own D5 row.
CAPACITY_NOTE_BREACH = ("  capacity: census verdict BREACH — the room is already over "
                        "cap.agent_panes. Every counted candidate is DEFERRED.")
# 7.278's own addition, ruled `p-7278-wire-form-confirmed`: C1 §2.1 defines COUNTED by membership
# in `counting.counts_toward_cap` and is SILENT on a descriptor that declares no `agent_type`. The
# literal definition is followed (absent ⇒ not counted) and the seat is NAMED, because
# `budget.json`'s own `counting.unclassified_with_descriptor` rule is "never silently counted and
# never silently skipped" — and an unnamed skip here is a seat that quietly escaped the cap.
CAPACITY_NOTE_UNDECLARED = ("  {agent}: capacity — descriptor declares NO `agent_type`, so it is "
                            "outside counting.counts_toward_cap and spends NO cap slot. It is "
                            "named because an unnamed skip is a seat that quietly escaped the cap; "
                            "declare the type in its descriptor to bring it under the cap.")

# ---------- 7.406: COLD-START ADMISSION — G-leader-0805-2036 -----------------------------------
#
# 7.363 made an ABSENT-or-STALE census DEFER — correct for a room that has run before and whose
# sensor died. It also defers a VIRGIN package, one no sensor has EVER run against and no seat has
# EVER launched into — the census reader below never finds a `state.json` to read there. The
# pickup lane 7.363 names ("restore the census") can never fire on a room nothing has ever written
# to, so every package the wired entry creates launched ZERO seats on its own first act. This
# section admits exactly that one state, on the empty-room bound, and touches no other reading.
#
# ⚠ THE SENSOR THAT USED TO WRITE `state.json` IS DELETED [T4-R8, del-observers]: "is it alive" is
# answered by the supervisor registry (not yet built), never by a pane or a census file. Every
# room now reads as this same cold-start/absent-census state, permanently — this section's
# admission logic already treats that as a valid, handled state rather than a crash, so nothing
# here needed to change to keep functioning; it simply now fires on every room, not only virgin
# ones.
def _cap_marker_absent(path):
    """True ONLY on a positively-confirmed absence (`FileNotFoundError`). Present, unreadable, or
    any other `OSError` (permission denied, a path segment that is a file, ...) all return False —
    the predicate's one failure direction is toward "not absent", never toward "absent"."""
    try:
        os.stat(path)
        return False
    except FileNotFoundError:
        return True
    except OSError:
        return False


# Carried VERBATIM, same discipline as the lines above: no policy number in the string, `{pkg}` is
# the caller's own package path.
CAPACITY_COLDSTART_LINE = (
    "  capacity: COLD-START — no sensor has ever run against {pkg} and no seat has ever launched "
    "into it (state.json ABSENT, no coordination/team-monitor.log, no writer-lock, no "
    "sessions.csv — every marker read fails closed on any other outcome). Admitted on the "
    "EMPTY-ROOM BOUND: in_use 0, headroom cap.agent_panes, never more.")


def _cap_admit_upto(workers, counted_types, allow):
    """(admitted, deferred, taken) — the SAME admit-up-to-`allow` shape the full-capacity branch
    below uses inline, factored out here so the cold-start call site carries no digit of its own:
    `allow` is read from `budget.json` at the call site, never written in this function."""
    taken = 0
    admitted = []
    deferred = []
    for w in workers:
        atype = w.get("agent_type") or ""
        if atype in counted_types:
            if taken < allow:
                taken += 1
                admitted.append(w)
            else:
                deferred.append(w)
        else:
            admitted.append(w)
    return admitted, deferred, taken


def cmd_session_open(args):
    """Open the named seat's session-trace row — `session_open` as a CALLABLE VERB.

    WHY IT EXISTS (7.446 / MC4, finding A of briefing-m6-missing-capabilities). `session_open` is
    the ONLY function that CREATES a row in a package's `sessions.csv`, and production reached it
    from exactly ONE site — `launch_seat:11613`, inside this file. Every other trace call is a
    MUTATOR that requires the row to already exist. So a launcher that is not `launch_seat` — the
    daemon's own spawn path — could not create a trace at all, and the advancement pass of the day
    correctly refused a package with no trace: no edge advanced on the daemon. This verb is the
    act that path can invoke. It CALLS `session_open`; it does not reimplement it, and it changes
    neither `session_open` nor any of the six mutators.

    ⚠ THE REFUSAL THAT EARNED IT IS RETIRED, THE REASON IS NOT. That pass is deleted with the
    second readiness evaluator (`one-readiness-predicate`), and the surviving one —
    `ready_seat_rows`, here — reads `sessions.csv` for the undeclared-ending term and for the
    durable disposition. A daemon-launched seat with no trace row is still a seat this file cannot
    reason about; the verb is still how that launcher opens one.

    ⚠ IT IS NOT A LICENCE TO HAND-WRITE THE TRACE. The
    row it writes is `session_open`'s row, written by the kit, for a seat that has a descriptor in
    THIS package — and the caller is expected to have just brought that seat up. A row for a seat
    that never booted is the G-11 lie; the ORDERING is the caller's to get right (`launch_seat`
    writes only after `wait_harness_up` returns), and this verb cannot check it for them.

    Two refusals and one no-op, all three of them the caller's contract:
      - no descriptor for the named seat in this package -> REFUSE. There is nothing to build a
        row from: `session_open` reads the seat's harness and cwd off its descriptor, and inventing
        them would fabricate a session's identity.
      - the seat already has an OPEN row -> NO-OP, exit 0, the existing session-id printed. A
        launcher that retries must not leave two open rows for one seat.
      - anything `session_open` raises -> reported, exit 1. The trace is bookkeeping about the
        run, so `launch_seat` swallows its failures (`session_trace_safe`) rather than fail a live
        seat. HERE the write IS the whole act: a caller that asked for a row and got none must
        learn it, or it will believe a trace exists that does not.
    """
    pkg = package_dir(args)
    seats = [w for w in discover_workers(workers_dir(args)) if w["agent"] == args.seat]
    if not seats:
        known = ", ".join(sorted(w["agent"] for w in discover_workers(workers_dir(args)))) or "(none)"
        refuse("state",
               f"no seat descriptor carries `agent: {args.seat}` in {workers_dir(args)}, so this "
               f"package has no such seat and there is nothing to open a session for. A trace row "
               f"is NEVER fabricated for a name the package does not know — a trace row asserts a "
               f"seat BOOTED, and one written for a name that has no descriptor asserts it about "
               f"nothing.\n"
               f"seats in this package: {known}", 1)
    already = session_open_id(pkg, args.seat)
    if already:
        print(f"{args.seat}: session {already} is ALREADY OPEN — nothing written. "
              f"(A second call for a live seat is a no-op, so a retrying launcher cannot "
              f"double-write the trace. Close it first if this is a NEW session: "
              f"`{coord_invocation(args)} close-seat {args.seat}`.)")
        return
    res, terr = session_trace_safe(session_open, args, seats[0],
                                   since=time.time(), wait=args.wait, pane=args.pane)
    if terr:
        refuse("environment",
               f"the session row for {args.seat} was NOT written — {terr}. NOTHING was recorded, "
               f"so do not treat this package as traced.", 1)
    sid, note = res
    print(f"{args.seat}: session {sid} opened in {sessions_csv(pkg)}")
    if note:
        print(c(f"  {note}", C_HINT))

# ---------- E22 (owner ruling, 2026-08-23) · THE LANE-AWARE LAUNCH COMPOSER ----------------------
#
# `G-leader-0822-2056` / `G-leader-0822-2058` (the parked-on-console diagnosis): every leader-direct
# launch door — a bare `launch`, `--only`, `--declare-only`, `--rerun`, `--reopen` — composed a tmux
# pane running a bare harness, LANE-BLIND. On a goal whose `execution-lane` marker reads `daemon`
# that is an UNCAGED sitting (no bwrap, no seat.md descriptor carriage) — and from inside a cage it
# cannot even read a sibling seat's descriptor (SeatBinds `ro-mask:{goalDir}/seats`), so the boot
# prompt read "Read your briefing None first". The leader therefore held NO caged re-run act for an
# `exited`/UNDECLARED daemon-lane row, and the whole class parked on the owner at a terminal.
#
# THE FIX IS ONE BRANCH AFTER ADMISSION. Every wall above it — P2–P4 of `--rerun`, the 7.251 wall of
# `--declare-only`, `--reopen`'s brake and walk-forward, the D45/F17
# identity bound, the admission filter, PROP-8, the capacity term — is untouched and decides the
# same on both lanes. (`is_authorized_launcher`, the per-verb role predicate `launch` used to be
# gated on, is gone [T2-R10, D24, F-simplicity-7] — `launch` is callable by any resolved identity
# now.) What moves is the COMPOSER: on the daemon lane the admitted seats are handed
# to the daemon's OWN spawn door — gateway intent `enqueue-job` on the seat's registered job
# (`seat-<goal>-<seat>`, the id `supervisor/seeding.js#jobIdFor` registers at seeding), headless, the
# canonical seat folder as workdir and NO prompt — the same row `supervisor/reconcile.js#launchSitting`
# enqueues for a watcher relaunch. The daemon then composes the cage (`server/spawn/spawn.js`:
# `composeCageFor` + `buildBwrapArgv`, the real `seat.md` descriptor) and — because a caged caller
# cannot compose it — the boot prompt (`server/ticker/ticker.js#launchAgent` asks
# `supervisor/seeding.js#seatBootPrompt`, i.e. `coordinate boot-prompt --lane daemon`, at dispatch),
# and opens the seat's `sessions.csv` row at dispatch exactly as for every watcher relaunch. One
# composer per lane; no second copy of the cage; no second Python writer into `heart.db` (the
# gateway IS the daemon's single writer — the hazard `--reopen`'s wall names).
#
# The prior row stays as it stands (D42's `exited`, D54's `done`, the UNDECLARED cell) and is
# superseded by the daemon's new row. A dedup refusal from the door (a live/queued sitting already
# holds the seat) is PRINTED AS A REFUSAL and counted out of `launched` — never reported as
# launched. `--tmux-target` is REFUSED on this lane, never silently ignored. The console lane
# composes byte-identically to before (the self-test's E22-3 control).
#
# AUTHZ, measured: `server/internal-api/dispatch.js#handleEnqueueJob` runs NO authz predicate —
# `enqueue-job` is open to every authenticated sender by design ("a live feed can do strictly LESS
# than an enqueue … which is open to any authenticated sender"), so no allow-rule is minted; there
# is no leader-only admission on `launch` anymore either [T2-R10, D24, F-simplicity-7] — the role
# predicate that used to gate it here (`is_authorized_launcher`) is deleted.

_GOAL_CLI_TOOL_DIR = Path(__file__).resolve().parent.parent / "operator" / "goals-tree" / "tool"


def goal_execution_lane(pkg):
    """`daemon` or `console` for this package's `execution-lane` marker — read through the goals
    tree's OWN Python speller (`goal_cli.read_lane`, DEC-1's twin of `lane-watch.js#readLane`),
    never a third copy of the grammar in this file (the W1 note on `cmd_boot_prompt`). The import
    is lazy (this is the one verb that needs it) and resolved relative to this file, exactly as
    `materialize-seats.py` resolves the same module. An import failure is a LOUD refusal, never a
    silent `console`: a launch that cannot tell its lane must not open an uncaged pane."""
    try:
        if str(_GOAL_CLI_TOOL_DIR) not in sys.path:
            sys.path.append(str(_GOAL_CLI_TOOL_DIR))
        from goal_cli import read_lane as _read_lane  # noqa: E402 — lazy by design
    except Exception as exc:  # noqa: BLE001 — any import failure is the same refusal
        refuse("environment",
               f"cannot read this goal's execution lane: the goals-tree speller "
               f"`goal_cli.read_lane` did not import from {_GOAL_CLI_TOOL_DIR} "
               f"({type(exc).__name__}: {exc}). A launch that cannot tell `daemon` from `console` "
               f"must not guess — on the daemon lane a guessed `console` opens an UNCAGED pane. "
               f"Nothing was opened.", 1)
    lane, _legacy = _read_lane(Path(pkg))
    return lane


# ── `--rerun`'s ADMITTED FROM-STATE, spelled once [D42, spec-supervisor §4, T1-R3] ─────────────
# The door admits a CRASH and nothing else. `crash` is the ordinary death with no checkout;
# `provider-error` is the same death whose evidence named the model provider — the supervisor
# classifies it separately so spec-recovery can reroute rather than strike, but from THIS door's
# side both are "the harness died and the work is unknown", which is exactly what a re-run answers.
# `outputs-missing` is deliberately absent: that is the gate's verdict on a claim the seat made, a
# ruling and not a re-run, and admitting it here would make this door "anything but done".
RERUN_ADMITTED_REASON_CLASSES = frozenset({"crash", "provider-error"})


def daemon_lane_reason(door, why):
    """The admission brake's `reason` token for a leader-direct daemon-lane launch: the DOOR and the
    leader's own anchor/reason, folded to the door's token grammar (`^[a-z][a-z0-9_-]{0,63}$`,
    runtime/gateway/parse.js). Per-anchor ON PURPOSE: the brake (heart-store.js, D52/D66) admits at most
    ADMISSION_BRAKE_LIMIT launches per (goal, seat, reason) with an unchanged signature, and this
    door's signature is the args bytes — constant per seat — so the anchor is what separates one
    investigation's budget from the next (D66's own `(goal, seat, reason)` shape, one token)."""
    slug = re.sub(r"[^a-z0-9_-]+", "-", (why or "").lower()).strip("-")
    tok = f"leader-{door}" + (f"-{slug}" if slug else "")
    return tok[:64].rstrip("-")


def launch_daemon_lane(args, workers, pkg, adm_fold, blocked, adm_deferred, door, why,
                       reopen_downstream=()):
    """The daemon-lane COMPOSER of `cmd_launch` — reached only after every admission wall admitted
    `workers`. Opens NO pane. Dry-run prints the enqueue each seat would get and exits on the same
    fold the console dry-run exits on; the real path POSTs one `enqueue-job` per seat through the
    gateway and renders the same verdict block (`launched`/`refused`, exit 1 on any refusal) the
    console path renders — a dedup or brake refusal from the door IS a refusal here."""
    goal = Path(pkg).name
    # ⚠ THE DOOR IS ON THE SUPERVISOR'S LIST OR THIS LAUNCH IS UNSUPERVISED [T4-R7]. The token
    # composed below travels as the enqueue's `reason`, and `supervisor/doors.js#doorForLauncher`
    # reads it back at the pid moment to decide which door the registry row names. A door spelled
    # here and not there produces a launch that silently registers as unsupervised, so the two
    # spellings are checked against each other in the act rather than trusted to stay in step.
    if door == "rerun" and not supervisor_door.door_is_wrapped("rerun"):
        refuse("state",
               "the `--rerun` door is not wrapped by the supervisor, so this launch could not be "
               "registered as a supervised sitting. NOTHING was enqueued and NO pane was opened.",
               1)
    reason = daemon_lane_reason(door, why)
    rows = [(w, w["agent"], str(Path(pkg) / "seats" / w["agent"]), f"seat-{goal}-{w['agent']}")
            for w in workers]
    if args.dry_run:
        for w, seat, seat_dir, job_id in rows:
            verr = validate_seat(w)  # PROP-8: the same pre-flight the console dry-run shows
            shape = (f"enqueue-job job_id={job_id} session_mode=headless trigger_kind=scheduled "
                     f"reason={reason} args={{\"workdir\": \"{seat_dir}\"}} — no tmux pane and no "
                     f"harness argv here: the daemon composes the cage (bwrap + seat.md) and the "
                     f"boot prompt (`boot-prompt --lane daemon`) at dispatch")
            print(f"[dry-run] {seat} ({w['harness']}/{w['model'] or 'plan-default'}"
                  f"{'/' + w['effort'] if w['harness'] == 'claude' else ''}, daemon lane -> "
                  f"enqueue, workdir={seat_dir}): {('REFUSED — ' + verr) if verr else shape}")
        if adm_fold:
            print(c(f"launch INCOMPLETE (dry-run): {len(adm_fold)} seat(s) would NOT launch "
                    f"({', '.join(adm_fold)}). The exit code is the same one a real launch of "
                    f"this set would return.", C_DEAD), file=sys.stderr)
            sys.exit(1)
        return
    target = gateway_transport_target(args)
    if not target:
        refuse("environment",
               "this goal's execution-lane is `daemon`, so launch hands the seat to the daemon's "
               "own spawn door — and no daemon serves this workspace (no server.json machine "
               "entry and no IGNITE_GATEWAY_ADDR). Nothing was enqueued and NO pane was opened: "
               "an uncaged pane is not a fallback for a daemon-lane goal.", 1)
    host, port, token = target
    run_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    refused = []
    for w, seat, seat_dir, job_id in rows:
        label = f"{seat} ({w['harness']}/{w['model'] or 'plan-default'}, daemon lane)"
        payload = {"job_id": job_id, "args": {"workdir": seat_dir}, "session_mode": "headless",
                   "trigger_kind": "scheduled", "run_at": run_at, "reason": reason}
        try:
            _status, envelope = gateway_client.call_gateway(host, port, "enqueue-job", payload,
                                                            token=token)
        except gateway_client.GatewayTransportError as exc:
            print(f"  {label}: FAILED — the daemon's door could not be reached: {exc}",
                  file=sys.stderr)
            refused.append(seat)
            continue
        if not isinstance(envelope, dict) or envelope.get("ok") is not True:
            err = (envelope.get("error") if isinstance(envelope, dict) else None) or {}
            code = err.get("code") if isinstance(err, dict) else None
            msg = err.get("message") if isinstance(err, dict) else repr(envelope)
            hint = ""
            if code == "AUTH_REFUSED":
                hint = (" — no sender token reached the gateway: IGNITE_SENDER_TOKEN in the "
                        "environment, or `.rbtv/config/sender-token.env` under the workspace root "
                        "(the one file a seat cage never masks)")
            elif "unknown job" in str(msg):
                hint = (f" — the daemon has no registered job `{job_id}` for this seat: this goal "
                        f"was never seeded on the daemon lane (supervisor/seeding.js registers one per "
                        f"taskforce row on its first daemon pass)")
            print(f"  {label}: FAILED — the daemon's door refused the enqueue: "
                  f"{code or 'UNKNOWN'}: {msg}{hint}", file=sys.stderr)
            refused.append(seat)
            continue
        result = envelope.get("result") or {}
        if result.get("deduped"):
            print(f"  {label}: NOT ENQUEUED — the daemon already holds a live or queued sitting "
                  f"for this seat (deduped: held by {result.get('because')}, queue "
                  f"{result.get('jobId')}, exec {result.get('exec_id')}). This is the door's "
                  f"REFUSAL, not a launch — a second sitting under one seat is never opened.",
                  file=sys.stderr)
            refused.append(seat)
            continue
        if not result.get("jobId"):
            print(f"  {label}: NOT ENQUEUED — the daemon's door returned no queue row: its "
                  f"admission brake (D52/D66, per goal+seat+reason) refused this launch. A "
                  f"genuinely NEW investigation needs its own anchor/reason; an owner act re-arms.",
                  file=sys.stderr)
            refused.append(seat)
            continue
        print(f"enqueued {label} as daemon queue row {result['jobId']} — a caged headless "
              f"sitting; the daemon opens the seat's sessions.csv row at dispatch (job {job_id})")
    if door == "reopen" and why and len(workers) > len(refused):
        seat = workers[0]["agent"]
        down = (f" {len(reopen_downstream)} seat(s) already ran depending on the retracted "
                f"`done`: {', '.join(reopen_downstream)} — flagged, NOT rolled back (D54/D72)."
                if reopen_downstream else "")
        num = append_message(base_dir(args), DISPOSITION_WRITER_KIT, "leader", "note",
                             f"reopen: `{seat}` was re-opened on the daemon lane (reason `{why}`) "
                             f"on top of a `done` row; the daemon opens the new sessions.csv row "
                             f"at dispatch, so the reason is recorded HERE rather than on a row "
                             f"this act never wrote.{down}")
        print(c(f"  {seat}: reopen reason recorded on the bus (messages.md #{num}) — on the "
                f"daemon lane the new sessions.csv row is the daemon's, opened at dispatch, so "
                f"the `{REOPEN_REASON_COL}` cell is not written by this act.", C_HINT))
    launched = len(workers) - len(refused)
    refused = refused + [w["agent"] for w in blocked] + [w["agent"] for w, _c_, _r_ in adm_deferred]
    if refused:
        print(c(f"launch INCOMPLETE: {launched} enqueued, {len(refused)} refused "
                f"({', '.join(refused)}). The enqueued seats are QUEUED with the daemon and were "
                f"not rolled back.", C_DEAD), file=sys.stderr)
        sys.exit(1)
    print(c(f"next: {coord_invocation(args)} ready-seats --explain <seat> — the daemon dispatches "
            f"the queued sitting on its next tick and opens the seat's sessions.csv row; a "
            f"refusal at dispatch lands on the bus", C_HINT))


def cmd_launch(args):
    # ---- F17 ENTRY BOUND: refuse an UNCORROBORATED `--as` identity BEFORE anything is read,
    # resolved or opened. First statement of the command on purpose — the guard's whole claim is
    # that it acted on nothing, and every statement below it reads the package.
    if not args.dry_run:
        _f17_claim, _f17_pane = asserted_launch_claim(args)
        if _f17_claim:
            refuse("identity", ASSERTED_LAUNCH_REFUSAL.format(
                claim=_f17_claim,
                pane_state=asserted_launch_pane_state(_f17_pane),
                invocation=coord_invocation(args)), 2)
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — `launch` is callable by any
    # resolved identity. #210: the roster is still resolved FIRST because the memory gate is
    # sized by seat COUNT; `--dry-run` opens nothing, so it skips the memory gate too.
    workers = seats_by_name(args, args.only)
    if args.dry_run:
        gate(args, "launch")
    else:
        launch_gates(args, "launch", len(workers) or 1)
    # G-51: the descriptor binds and the registry is a record nothing read until now. Checked on
    # the DRY-RUN path too — a dry-run exists to show what a real launch would do, and hiding a
    # divergence from it would make the one command meant for inspection the one that lies.
    check_bindings(args, workers, "launch")
    if not workers:
        refuse(
            "state",
            f"no worker briefing carries an `agent:` frontmatter key in "
            f"{workers_dir(args)}, so there is no roster to launch.\n"
            f"Each seat needs workers/<agent>/agent.md with `agent: <name>` "
            f"(template: briefing-template.md beside coord.py).",
            1)

    # ==== E22 (owner, 2026-08-23) — THE LANE IS READ ONCE, HERE, and decides the COMPOSER far below
    # (`launch_daemon_lane`); every admission wall between here and there runs unchanged on both
    # lanes. Read through the goals-tree's own speller (`goal_execution_lane`), never derived here.
    # `--tmux-target` is refused on the daemon lane AT ONCE — before any ADMITTED banner prints —
    # because it names a pane this lane never opens, and a flag silently ignored is a flag that lies.
    _lane = goal_execution_lane(package_dir(args, register=False))
    if _lane == "daemon" and str(getattr(args, "tmux_target", "") or "").strip():
        refuse("input",
               f"--tmux-target names a tmux pane, and this goal's `execution-lane` is `daemon`: "
               f"launch hands the seat to the daemon's own spawn door (a caged headless sitting) "
               f"and opens NO pane, so the flag has nothing to name here. Refused rather than "
               f"ignored. Drop it: {coord_invocation(args)} launch --only <seat> ...", 2)

    # 7.241 (U4.6): THE UNDECLARED-ENDING REFUSAL — the CONSUMER of 7.237's detector on the ONE
    # path that opens panes. `undeclared_endings` is 7.237's function, called here and not
    # reimplemented: this adds NO detector, it wires the existing one to a caller that acts.
    #
    # WHY HERE AND NOT ONLY IN `ready_seat_rows`: 7.237 put the class into the READY arithmetic,
    # which removes these seats from what the offer lane is HANDED. But `launch` reads the
    # `after` field zero times and calls no readiness computation, so `launch --only <seat>`
    # walked straight past it — 7.237 declared exactly that as its residue. A verdict nothing on
    # the launch path consults is a log line to this command.
    #
    # WHAT IT PREVENTS: relaunching a seat whose session ENDED with an EMPTY disposition re-runs
    # work that already CONCLUDED. The empty cell is a missing assertion, never missing work.
    #
    # ⚠ NO *OVERRIDE* FLAG CARRIES THIS, and that is deliberate, not an oversight. It is NOT on
    # `--force` (which carries the ROLE gate alone) and NOT on `--force-memory`; re-attaching a
    # second gate to either is barred by the run's standing bar, and 7.251 attaches nothing to
    # either — THE BARRED LIST IS UNCHANGED BY THE ADMISSION BELOW. An undeclared ending is a
    # DEFECT FOR THE `leader` — it either gets the ending declared or rules the row — and it is
    # never a relaunch instruction, so there is nothing for an override to express. Nobody but the
    # occupant witnessed what that session meant, and no caller here may assert it on its behalf.
    #
    # ⚠⚠ 7.251 (C1.2) — `--declare-only <leader-anchor>` IS A SEPARATE, PURPOSE-CARRIED ADMISSION
    # AND IS NOT AN OVERRIDE. Read this before concluding the paragraph above is now false; it is
    # not, and the distinction is the whole design (`p-C1-2-comment-amendment-approved-with-three-
    # bounds`, on the reconciliation in `admission-predicate-spec.md` §6):
    #
    #   (1) IT DOES NOT OVERTURN THE VERDICT. After admission the target is STILL UNDECLARED and
    #       every reader still says so. Nothing about the dead session changes. The verdict clears
    #       later by SUPERSESSION — when the admitted session writes its OWN ended row.
    #   (2) IT ADMITS A DIFFERENT ACT. The harm named above is "relaunching … re-runs work that
    #       already CONCLUDED". A session that declares its own ending and checks out re-runs
    #       NOTHING, so that harm does not reach it.
    #   (3) IT *IS* THE REMEDY THIS COMMENT ALREADY ROUTES TO. The `leader` "either gets the
    #       ending declared or rules the row"; until 7.251 no tool admitted the FIRST arm. This is
    #       that arm, and it carries the `leader`'s own anchor as its VALUE — so it is reachable
    #       only by way of the investigation this comment demands.
    #
    #   THE BARRED LIST IS UNTOUCHED AND STAYS UNTOUCHED: `--force` carries the ROLE gate alone, a
    #   memory refusal answers to `--force-memory` alone, and NO gate is ever re-attached to
    #   either — by this change or any successor. `--declare-only` is a THIRD, independent
    #   parameter; a reader who finds it beside them and infers a family has inferred wrong.
    #
    # SCOPED TO WHAT THE CALLER TARGETED: the class is filtered OUT of the launch set, so a mass
    # launch still opens every other seat. The command refuses outright only when the filter
    # empties the set — which is precisely the `--only <undeclared-seat>` case.
    #
    # BOTH BRANCHES CARRY THE SAME PREDICATE (G-257's lesson, argued a few lines above for the
    # role gate): the filter and the refusal run on `--dry-run` too. A dry-run exists to show
    # what a real launch would do; one that showed a pane opening where the real path refuses
    # would make the one command meant for inspection the one that lies. THE SAME RULE BINDS THE
    # ADMISSION: no `args.dry_run` test appears anywhere in the block below, so its verdict, its
    # text and its exit code are identical on both paths BY CONSTRUCTION rather than by promise.
    #
    # ⚠ THE ADMISSION IS EVALUATED FIRST, and only when it does NOT admit does the filter run.
    # Ordering it the other way would filter the target out of `workers` before anything could
    # admit it, leaving an instrument that is reachable in the parser and dead in the path.
    _decl_anchor = (getattr(args, "declare_only", None) or "").strip()
    _declare_only_admitted = False
    if _decl_anchor:
        # 7.251 / `admission-predicate-spec.md` §3 — ADMIT(T) iff P1 ∧ P2 ∧ P3 ∧ P4. Every clause
        # reads an EXISTING function or field; this block adds NO detector, exactly as the 7.241
        # gate above adds none. P1 is the parameter itself (an INPUT, it detects nothing) and is
        # true by the `if`.
        _pkg = package_dir(args, register=False)
        _only = [n.strip() for n in (args.only or "").split(",") if n.strip()]
        # P2 — exactly ONE seat, explicitly named. The anchor cites the `leader`'s investigation
        # of ONE undeclared ending, so it cannot be spread over a set the caller did not name.
        if not _only:
            refuse(
                "state",
                "--declare-only admits ONE named seat, and no seat was named. It carries the "
                "`leader`'s anchor for a SPECIFIC undeclared ending, so it cannot be applied to "
                "a set the caller did not name — a mass launch has no per-seat anchor to cite.\n"
                f"Name the seat: {coord_invocation(args)} launch --only <seat> "
                "--declare-only <leader-anchor>\n"
                "A mass launch needs no flag: undeclared seats are filtered out of it and every "
                "other seat still opens.",
                1)
        if len(_only) > 1:
            refuse(
                "state",
                f"--declare-only admits ONE seat per invocation, and --only named {len(_only)}: "
                f"{', '.join(_only)}.\nThe anchor you passed cites the `leader`'s investigation "
                "of ONE undeclared ending; applying it to several would cite one investigation "
                "as evidence for endings it never examined.\n"
                "Run it once per seat, each with that seat's own anchor.",
                1)
        _t = _only[0]
        # P3 — the target's LAST ENDED row exists and its disposition cell is EMPTY. Both reads
        # are the 7.241 gate's own, and `last_ended` is injected so the file is read once.
        _le = sessions_last_ended(_pkg)
        _undec = undeclared_endings(_pkg, last_ended=_le)
        if _t not in _le:
            refuse(
                "state",
                f"'{_t}' has no ENDED session row in this package, so there is no undeclared "
                "ending to declare and --declare-only has nothing to admit.\n"
                f"A seat that has not ended is an ordinary launch candidate: "
                f"{coord_invocation(args)} launch --only {_t}\n"
                f"If you expected an ended row, read it first: {coord_invocation(args)} "
                f"ready-seats --explain {_t}",
                1)
        if _t not in _undec:
            # ⚠ THE BRANCH THAT CLOSES THE RE-RUN HOLE, and it closes it BY STATE. P1 (purpose) is
            # caller-asserted and unfalsifiable — a caller who wanted to re-run finished work
            # passes the same flag as one who did not (the carve-out diff over every readable
            # field is EMPTY, `admission-predicate-spec.md` §8). P3 is package STATE and no caller
            # can assert it. So: P3 bounds the HARM, P1 bounds the ACT, and neither substitutes.
            refuse(
                "state",
                f"'{_t}' last ENDED with a DECLARED disposition (`{_le[_t][1]}`), so it is not in "
                "the undeclared class and --declare-only does not admit it. The ending is already "
                "on the record; there is nothing left to declare.\n"
                "THIS REFUSAL IS BY STATE, NOT BY PURPOSE: it is the same refusal whatever the "
                "caller intended, and it is what closes the re-run hole. A declared ending means "
                "the work CONCLUDED and was accounted for — relaunching it re-runs finished work, "
                "which is the harm the launch gate exists to prevent, and an honest purpose does "
                "not make that harm smaller.\n"
                f"Read the row: {coord_invocation(args)} ready-seats --explain {_t}",
                1)
        # P4 — no LIVE pane already holds the name. This re-uses P37's own composition and adds no
        # detector; P37 remains the backstop at check-in. Without P4 the launch would succeed, a
        # pane would open, and the seat would fail one command later holding a pane nobody asked
        # for. P37 also tests `prior["pane"] != pane` (its caller's own), which has no meaning
        # here: at `launch` no candidate pane exists yet.
        _, _, _rows = load_workers(base_dir(args))
        _prior = current_row(_rows, _t)
        if (_prior and _prior.get("active") == "yes" and _prior.get("pane")
                and liveness.occupied(package_dir(args, register=False), _t,
                                      _prior["pane"] in live_panes())):
            # THE PREDICATE IS THE REGISTRY, NOT THE PANE [T4-R8, spec-supervisor §6]: a pane
            # outlives its harness and a daemon-lane sitting never had one. `occupied` collapses
            # the three-valued answer once and fails CLOSED where the sitting is unsupervised.
            refuse(
                "state",
                f"'{_t}' is already checked in on pane {_prior['pane']}, and tmux says that pane "
                "is still ALIVE — admitting a declare-only session now would put two live "
                "sessions under one name (P37).\nNeither would see the other's messages (the "
                "unread filter is keyed on the name) and only the newest pane would receive "
                "wakes.\nConfirm the old session is dead first: inspect it with `tmux "
                f"capture-pane -p -t {_prior['pane']}`; if it is a zombie, kill it BY PANE ID "
                f"(`tmux kill-pane -t {_prior['pane']}`) — never by name — then retry.\n"
                "NO pane was opened.",
                1)
        # ADMITTED. P2 made the launch set exactly this one seat, so skipping the filter below
        # cannot let any OTHER undeclared seat through.
        _declare_only_admitted = True
        print(c(f"  {_t}: ADMITTED by --declare-only — session "
                f"`{_undec[_t]}` ended UNDECLARED and stays UNDECLARED. This admits a session "
                f"that DECLARES ITS OWN ENDING and does nothing else; it asserts nothing about "
                f"the dead one, and the verdict clears only by supersession when this session "
                f"writes its own ended row.\n  trail (the `leader`'s anchor, recorded not "
                f"verified — no tool can check that an anchor names a real investigation): "
                f"{_decl_anchor}", C_HINT))

    # ⚠⚠ D42 (owner, 2026-08-20) — `--rerun <LEADER-ANCHOR>` IS A FOURTH, INDEPENDENT PARAMETER,
    # AND IT IS NOT AN OVERRIDE. Everything the 7.251 wall above says about `--declare-only` says
    # itself again here and is not repeated; what differs is the STATE it is bounded by and the ACT
    # it admits, and those two differences are the whole instrument:
    #
    #   P3 (STATE) — the target's LAST ENDED row carries `exited` WRITTEN BY THE KIT. That is the
    #       one ending nobody witnessed: `attest-exit` records THE HARNESS TERMINATED and nothing
    #       about the work. `--declare-only`'s P3 is the opposite state (an EMPTY cell), so the two
    #       instruments can never admit the same row and neither widens the other.
    #   THE ACT — this admits an ORDINARY WORKING SESSION. The seat boots on its ordinary boot
    #       prompt and does its job. That is legitimate here for the reason the 7.241 wall's harm
    #       sentence gives and denies to every other class: "relaunching … re-runs work that
    #       already CONCLUDED" — a crashed harness's work did NOT conclude, and no reader claims it
    #       did. `exited` asserts termination, never completion, and NOTHING ANYWHERE MAPS IT TO
    #       `done` (see `DISPOSITION_WRITER_SEAT`'s wall).
    #
    # ⚠ IT REWRITES NOTHING. The `exited` row is left exactly as it stands and is SUPERSEDED when
    # the new session writes its own ended row — the same supersession model `--declare-only`
    # already describes. No `rule-disposition` is required first, and that is deliberate (D42, on
    # the live leader's own objection `meet/issues.md#G-leader-0820-1727`): a CLEAR would destroy
    # the `exited` word, which is the run's ONLY record of how that session ended.
    #
    # ⚠ IT MINTS NO ROLE GATE. `launch` carries no per-verb role predicate anymore
    # [T2-R10, D24, F-simplicity-7] — it is callable by any resolved identity, daemon included —
    # so this act adds none either. A second copy of the role model is the PRIN-11 defect this
    # file argues against everywhere else.
    #
    # THE BARRED LIST IS UNTOUCHED AND STAYS UNTOUCHED: `--force` carries the ROLE gate alone,
    # `--force-memory` the MEMORY gate alone, and neither admits an `exited` row — a reader who
    # finds this parameter beside them and infers a family has inferred wrong. D12 is intact: no
    # grant, no store, no flag file, no latch, no TTL, nothing to mint, lose or spend.
    #
    # ⚠ NO `--dry-run` TEST APPEARS ANYWHERE IN THIS BLOCK, for 7.251's reason and under its rule:
    # the verdict, the text and the exit code are identical on both paths BY CONSTRUCTION. The
    # 7.251 PARITY (construction) row slices this region out of the SOURCE and asserts the
    # identifier is absent from it, so this block is held to that rule by the same assertion.
    _rerun_raw = getattr(args, "rerun", None)
    _rerun_anchor = (_rerun_raw or "").strip()
    _rerun_admitted = False
    if _rerun_raw is not None and not _rerun_anchor:
        refuse(
            "input",
            "--rerun carries the `leader`'s own investigation anchor as its VALUE, and an empty "
            "one would re-run a crashed seat citing nothing.\n"
            f"Name it: {coord_invocation(args)} launch --only <seat> --rerun <leader-anchor>",
            2)
    if _rerun_anchor:
        _rr_pkg = package_dir(args, register=False)
        _rr_only = [n.strip() for n in (args.only or "").split(",") if n.strip()]
        # P2 — exactly ONE seat, explicitly named. The anchor cites ONE investigation of ONE
        # crashed session, so it cannot be spread over a set the caller did not name.
        if not _rr_only:
            refuse(
                "state",
                "--rerun admits ONE named seat, and no seat was named. It carries the `leader`'s "
                "anchor for a SPECIFIC crashed session, so it cannot be applied to a set the "
                "caller did not name.\n"
                f"Name the seat: {coord_invocation(args)} launch --only <seat> "
                "--rerun <leader-anchor>",
                1)
        if len(_rr_only) > 1:
            refuse(
                "state",
                f"--rerun admits ONE seat per invocation, and --only named {len(_rr_only)}: "
                f"{', '.join(_rr_only)}.\nThe anchor you passed cites the `leader`'s "
                "investigation of ONE crashed session; applying it to several would cite one "
                "investigation as evidence for sessions it never examined.\n"
                "Run it once per seat, each with that seat's own anchor.",
                1)
        _rt = _rr_only[0]
        # P3 — THE STATE BOUND, and it is the branch that keeps this from being an override. It
        # reads the ONE row-selection home (`sessions_last_ended_rows`) and adds no detector.
        _rr_row = sessions_last_ended_rows(_rr_pkg).get(_rt)
        if _rr_row is None:
            refuse(
                "state",
                f"'{_rt}' has no ENDED session row in this package, so there is no crashed "
                "session to re-run and --rerun has nothing to admit.\n"
                f"A seat that has not ended is an ordinary launch candidate: "
                f"{coord_invocation(args)} launch --only {_rt}\n"
                f"If you expected an ended row, read it first: {coord_invocation(args)} "
                f"ready-seats --explain {_rt}",
                1)
        # ── THE FROM-STATE IS READ OFF THE ENDING STORE, AND THE WORD `exited` IS GONE ────────
        #
        # D42 admitted ONE from-state: `exited` written by the kit. That vocabulary was retired
        # [T1-R3, T4-R7] — `exited` was a fifth ending carrying NO reason at all, and the ending
        # store now REFUSES it at the write boundary. The same fact is spelled `failed` with a
        # mandatory reason class, stamped by the SUPERVISOR from evidence (spec-supervisor §4), so
        # the door's admitted from-state is `failed` + a crash-shaped reason class and its source
        # is the store rather than a `sessions.csv` cell no writer fills any more.
        #
        # THE DOOR IS NOT WIDENED BY THE RENAME. `failed` with any OTHER reason class
        # (`outputs-missing`, the gate's verdict) is still refused here and still routed by name
        # below, exactly as `unverified` was: this admits a CLASS, never "anything but done".
        _rr_ending = ending_store.get_current_ending(_rr_pkg, _rt) or {}
        _rr_disp = (_rr_ending.get("ending") or _rr_row.get("disposition", "") or "").strip()
        _rr_class = (_rr_ending.get("reason_class") or "").strip()
        _rr_writer = (_rr_ending.get("writer") or _rr_row.get("disposition-writer", "") or "").strip()
        if _rr_disp != "failed" or _rr_class not in RERUN_ADMITTED_REASON_CLASSES:
            # ⚠ THE REFUSAL NAMES THE RIGHT DOOR FOR THE CLASS IT FOUND. Every other non-terminal
            # ending already has an owner, and sending them all here would make this the fifth
            # copy of a routing table the file already carries once.
            _rr_door = {
                "incomplete": ("the SEAT said its work is unfinished, and the goal watcher "
                               "relaunches that class BY NAME on its own cadence (D33(a)) — this "
                               "door is not it"),
                "unverified": ("the SEAT claimed done and the gate could not grade the claim. "
                               "That is a ruling, not a re-run — `rule-disposition` was deleted "
                               "[T2-R12, T1-R9]; no replacement ruling instrument is wired here yet"),
                "": ("nobody declared an ending at all. That is the UNDECLARED class, and this "
                     "door's own instrument for it is `--declare-only <leader-anchor>`; the "
                     "ruling verb `rule-disposition` was deleted [T2-R12, T1-R9] — no replacement "
                     "ruling instrument is wired here yet"),
                "done": ("its own writer's word stands and its edge has already ADVANCED. There "
                         "is nothing to re-run and no ruling grants a power to rewrite it"),
                "failed": (f"the ending IS `failed`, but its reason class is "
                           f"`{_rr_class or '(none)'}` — not a crash. `outputs-missing` is the "
                           f"gate's verdict on a claim, which is a ruling and not a re-run"),
            }.get(_rr_disp, f"`{_rr_disp}` is not a crashed ending and this door does not admit it")
            refuse(
                "state",
                f"'{_rt}' last ENDED with disposition `{_rr_disp or '(empty)'}` written by "
                f"`{_rr_writer or '(nobody)'}`, and --rerun admits EXACTLY ONE from-state: "
                f"`failed` with reason class "
                f"{' or '.join('`' + rc + '`' for rc in sorted(RERUN_ADMITTED_REASON_CLASSES))} "
                f"— the supervisor saying a harness DIED with the work unknown "
                f"(spec-supervisor §4; the reason-less word `exited` is retired [T1-R3]).\n"
                f"THIS REFUSAL IS BY STATE, NOT BY PURPOSE: it is the same refusal whatever the "
                f"caller intended. Here, {_rr_door}.\n"
                f"Read the row: {coord_invocation(args)} ready-seats --explain {_rt}",
                1)
        # P4 — no LIVE pane already holds the name. `--declare-only`'s own composition, reused
        # verbatim; this adds no detector and P37 remains the backstop at check-in.
        _, _, _rr_rows = load_workers(base_dir(args))
        _rr_prior = current_row(_rr_rows, _rt)
        if (_rr_prior and _rr_prior.get("active") == "yes" and _rr_prior.get("pane")
                and liveness.occupied(package_dir(args, register=False), _rt,
                                      _rr_prior["pane"] in live_panes())):
            # THE PREDICATE IS THE REGISTRY, NOT THE PANE [T4-R8, spec-supervisor §6]: a pane
            # outlives its harness and a daemon-lane sitting never had one. `occupied` collapses
            # the three-valued answer once and fails CLOSED where the sitting is unsupervised.
            refuse(
                "state",
                f"'{_rt}' is already checked in on pane {_rr_prior['pane']}, and tmux says that "
                f"pane is still ALIVE — re-running it now would put two live sessions under one "
                f"name (P37).\nNeither would see the other's messages (the unread filter is "
                f"keyed on the name) and only the newest pane would receive wakes.\nConfirm the "
                f"old session is dead first: inspect it with `tmux capture-pane -p -t "
                f"{_rr_prior['pane']}`; if it is a zombie, kill it BY PANE ID (`tmux kill-pane -t "
                f"{_rr_prior['pane']}`) — never by name — then retry.\n"
                f"NO pane was opened.",
                1)
        # ADMITTED. P2 made the launch set exactly this one seat.
        _rerun_admitted = True
        print(c(f"  {_rt}: ADMITTED by --rerun — session `{_rr_row.get('session-id') or '?'}` "
                f"ended `failed`/`{_rr_class}`, stamped by the supervisor from evidence: the "
                f"harness DIED and the work is UNKNOWN, never finished. This admits an ORDINARY "
                f"WORKING SESSION — the seat boots on its own boot prompt and does its job. The "
                f"`failed` ending is NOT rewritten, cleared or relabelled by this act: it "
                f"stays on the record and is superseded when this session writes its own ended "
                f"row.\n  trail (the `leader`'s anchor, recorded not verified — no tool can check "
                f"that an anchor names a real investigation): {_rerun_anchor}", C_HINT))

    # ==== D54/D66/D72 (owner, 2026-08-22) — `--reopen`: RE-OPEN a `done` row by APPENDING =========
    #
    # A leader-written `done` may be RE-OPENED on a LATE FINDING, by APPENDING a new sitting with
    # a recorded reason — the `done` row stands UNREWRITTEN (D54). This block is `--rerun`'s own
    # shape, one door over: no role gate either [T2-R10, D24, F-simplicity-7], same P2/P4 guards,
    # same "ordinary working session, prior row not rewritten" framing.
    # It differs from `--rerun` in exactly the ways D54/D66/D72 require:
    #   - admits `done` (any writer `RECORD_DISPOSITION_WRITER["done"]` admits), where `--rerun`
    #     refuses it BY STATE (its own refusal text, quoted above, unchanged) — `done` does NOT
    #     join `--rerun`'s own admitted from-state, which stays `exited`+`kit` only;
    #   - WRITES the reason durably (D72: "a new column on the NEW sessions row") where `--rerun`'s
    #     anchor is console-only — the gap the mechanism lane measured and flagged;
    #   - is bounded by a (goal, seat, reason) budget (D66) — `--rerun` carries none;
    #   - computes and flags D72's walk-forward (downstream seats that already ran on the `done`
    #     this reopens) — `--rerun`'s target, `exited`, never advanced an edge, so it has no
    #     downstream-consumer analogue at all.
    #
    # ⚠ THE BRAKE IS coord.py-LOCAL, NOT brief 07's `heart.db` COUNTER, AND THAT IS A DISCLOSED
    # DEVIATION FROM A LITERAL "wire to the SAME key" READING. `HeartStore.enqueue()` (brief 07,
    # D52/D66) is `heart.db`'s SOLE writer by design ("everything goes through it" — brief 07's own
    # brief text; mirrors this file's own D3 "no proxy writers" ledger discipline). `--reopen`, like
    # `--rerun` beside it, is a LEADER-DIRECT door: on the CONSOLE lane it opens a tmux pane and
    # appends a `sessions.csv` row; on the DAEMON lane (E22, 2026-08-23) it hands the admitted seat
    # to the daemon's OWN door through the gateway (`launch_daemon_lane`), where the door's
    # (goal, seat, reason) brake applies under a per-reason token. It NEVER writes `heart.db`
    # itself — there is no `enqueue()` call in this file to attach a check to, and a second Python
    # writer into a live daemon's SQLite store while that daemon is running is exactly the kind of
    # shared-live-system risk this plan's own hazards file warns against. `reopen_attempt_count`
    # (above) is the console lane's brake: the same (goal, seat, reason) KEY SHAPE,
    # counted instead over THIS package's own `sessions.csv` — a store `--reopen` already owns
    # exclusively. It is deliberately the FAIL-CLOSED direction: it counts every prior reopen under
    # an unchanged reason whether or not that sitting progressed (this door does not evaluate D52's
    # mail-cursor/disposition progress signals), so it can only OVER-brake relative to the full
    # ruling, never under-brake. A seat's DOWNSTREAM relaunches — the watcher picking up the new
    # sitting's own non-`done` ending — DO reach brief 07's queue-side brake normally: nothing in
    # this block or in `supervisor/reconcile.js`/`supervisor/seeding.js` (untouched, per this seat's own
    # scope wall) exempts a reopened row from that path.
    _reopen_raw = getattr(args, "reopen", None)
    _reopen_reason = (_reopen_raw or "").strip()
    _reopen_admitted = False
    _reopen_downstream = []
    if _reopen_raw is not None and not _reopen_reason:
        refuse(
            "input",
            "--reopen carries the `leader`'s RECORDED REASON for re-opening a finished (`done`) "
            "seat as its VALUE, and an empty one would re-open finished work citing nothing.\n"
            f"Name it: {coord_invocation(args)} launch --only <seat> --reopen <reason>",
            2)
    if _reopen_reason:
        _ro_pkg = package_dir(args, register=False)
        _ro_only = [n.strip() for n in (args.only or "").split(",") if n.strip()]
        # P2 — exactly ONE seat, explicitly named, same reasoning as `--rerun`'s own P2: the
        # reason cites ONE late finding against ONE seat's finished work.
        if not _ro_only:
            refuse(
                "state",
                "--reopen admits ONE named seat, and no seat was named. It records the "
                "`leader`'s reason for re-opening ONE finished seat, so it cannot be applied to "
                "a set the caller did not name.\n"
                f"Name the seat: {coord_invocation(args)} launch --only <seat> "
                "--reopen <reason>",
                1)
        if len(_ro_only) > 1:
            refuse(
                "state",
                f"--reopen admits ONE seat per invocation, and --only named {len(_ro_only)}: "
                f"{', '.join(_ro_only)}.\nThe reason you passed cites a late finding against ONE "
                "seat's finished work; applying it to several would cite one finding as evidence "
                "against work it never examined.\nRun it once per seat, each with its own "
                "reason.",
                1)
        _rot = _ro_only[0]
        # P3 — THE STATE BOUND. Reads the ONE row-selection home (`sessions_last_ended_rows`),
        # the same one `--rerun` reads, adding no second selector.
        _ro_row = sessions_last_ended_rows(_ro_pkg).get(_rot)
        if _ro_row is None:
            refuse(
                "state",
                f"'{_rot}' has no ENDED session row in this package, so there is no finished "
                "work to re-open.\nAn unfinished seat is an ordinary launch candidate: "
                f"{coord_invocation(args)} launch --only {_rot}\n"
                f"If you expected an ended row, read it first: {coord_invocation(args)} "
                f"ready-seats --explain {_rot}",
                1)
        try:
            _ro_end = ending_store.get_current_ending(_ro_pkg, _rot) or {}
        except ending_store.EndingStoreError:
            _ro_end = {}
        _ro_disp = _ro_end.get("ending") or _ro_row.get("disposition", "")
        _ro_writer = _ro_end.get("who_stamped") or _ro_row.get("disposition-writer", "")
        if _ro_disp != "done":
            # ⚠ THE REFUSAL NAMES THE RIGHT DOOR FOR THE CLASS IT FOUND, mirroring `--rerun`'s
            # own routing table — a fifth copy of it is not built; this is `--reopen`'s own,
            # naming `--rerun` for the ONE class it is right about.
            _ro_door = {
                "exited": ("the KIT says the harness TERMINATED and the work is UNKNOWN — never "
                           f"finished. That door is `{coord_invocation(args)} launch --only "
                           f"{_rot} --rerun <leader-anchor>` (D42)"),
                "incomplete": ("the SEAT said its work is unfinished, and the goal watcher "
                               "relaunches that class BY NAME on its own cadence (D33(a)) — this "
                               "door is not it"),
                "unverified": ("the SEAT claimed done and the gate could not grade the claim. "
                               "That is a ruling, not a reopen — `rule-disposition` was deleted "
                               "[T2-R12, T1-R9]; no replacement ruling instrument is wired here "
                               "yet"),
                "": ("nobody declared an ending at all. That is the UNDECLARED class, and this "
                     f"door's own instrument for it is `--declare-only <leader-anchor>`"),
            }.get(_ro_disp, f"`{_ro_disp}` is not a finished ending and this door does not "
                            f"admit it")
            refuse(
                "state",
                f"'{_rot}' last ENDED with disposition `{_ro_disp or '(empty)'}` written by "
                f"`{_ro_writer or '(nobody)'}`, and --reopen admits EXACTLY ONE from-state: "
                f"`done` — a leader-written or seat-written FINISHED ending (D54).\n"
                f"THIS REFUSAL IS BY STATE, NOT BY PURPOSE: it is the same refusal whatever the "
                f"caller intended. Here, {_ro_door}.\n"
                f"Read the row: {coord_invocation(args)} ready-seats --explain {_rot}",
                1)
        if _ro_writer not in ("seat", "leader"):
            refuse(
                "state",
                f"'{_rot}'s `done` row was written by `{_ro_writer or '(nobody)'}`, which is not "
                f"seat or leader — an inconsistent record, not a re-openable one.",
                1)
        # D66: the (goal, seat, reason) brake budget — see the block comment above for why this
        # is coord.py-LOCAL rather than a read/write against brief 07's `heart.db` counter.
        _ro_budget = 2
        _ro_prior = reopen_attempt_count(_ro_pkg, _rot, _reopen_reason)
        if _ro_prior >= _ro_budget:
            refuse(
                "state",
                f"'{_rot}' has already been re-opened {_ro_prior} time(s) citing the SAME reason "
                f"(`{_reopen_reason}`) — the (goal, seat, reason) brake budget (D52/D66) admits "
                f"at most {_ro_budget} launches with no owner re-arm.\nA genuinely NEW finding "
                f"needs its OWN reason string. Nothing was written.",
                1)
        # P4 — no LIVE pane already holds the name, `--rerun`'s own composition, reused verbatim.
        _, _, _ro_rows = load_workers(base_dir(args))
        _ro_prior_row = current_row(_ro_rows, _rot)
        if (_ro_prior_row and _ro_prior_row.get("active") == "yes" and _ro_prior_row.get("pane")
                and liveness.occupied(package_dir(args, register=False), _rot,
                                      _ro_prior_row["pane"] in live_panes())):
            # THE PREDICATE IS THE REGISTRY, NOT THE PANE [T4-R8, spec-supervisor §6]: a pane
            # outlives its harness and a daemon-lane sitting never had one. `occupied` collapses
            # the three-valued answer once and fails CLOSED where the sitting is unsupervised.
            refuse(
                "state",
                f"'{_rot}' is already checked in on pane {_ro_prior_row['pane']}, and tmux says "
                f"that pane is still ALIVE — re-opening it now would put two live sessions under "
                f"one name (P37).\nNeither would see the other's messages (the unread filter is "
                f"keyed on the name) and only the newest pane would receive wakes.\nConfirm the "
                f"old session is dead first: inspect it with `tmux capture-pane -p -t "
                f"{_ro_prior_row['pane']}`; if it is a zombie, kill it BY PANE ID (`tmux "
                f"kill-pane -t {_ro_prior_row['pane']}`) — never by name — then retry.\n"
                f"NO pane was opened.",
                1)
        # D72: THE WALK-FORWARD, computed at ADMISSION so it prints even on a dry run, and
        # re-read after the real launch (below) so the message it is recorded in can quote the
        # session-id the new row actually got.
        _reopen_downstream = reopen_downstream_seats(_ro_pkg, _rot)
        # ADMITTED. P2 made the launch set exactly this one seat.
        _reopen_admitted = True
        print(c(f"  {_rot}: ADMITTED by --reopen — session `{_ro_row.get('session-id') or '?'}` "
                f"ended `done` (writer `{_ro_writer}`): a LATE FINDING against FINISHED work "
                f"(D54). This admits an ORDINARY WORKING SESSION — the seat boots on its own "
                f"boot prompt and does its job. The `done` row is NOT rewritten, cleared or "
                f"relabelled by this act: it stays on the record and is superseded when this "
                f"session writes its own ended row.\n  reason (recorded on the NEW row's "
                f"`{REOPEN_REASON_COL}` column): {_reopen_reason}", C_HINT))
        if _reopen_downstream:
            print(c(f"  ⚠ DOWNSTREAM (D72): {len(_reopen_downstream)} seat(s) already ran "
                    f"depending on '{_rot}'s retracted `done`: {', '.join(_reopen_downstream)}. "
                    f"Flagged, NOT rolled back — D54/D72 grant a new sitting and a flag, never a "
                    f"rewrite of anything downstream already did.", C_HINT))

    # ⚠⚠ BOUND BEFORE THE BRANCH, AND THE PLACEMENT IS THE FIX (`G-admission-predicate-prover-
    # 0803-0155`). The launch VERDICT far below reads `blocked` UNCONDITIONALLY —
    # `refused = refused + [w["agent"] for w in blocked]` — but the only assignment used to live
    # inside the `if not _declare_only_admitted:` body, which is exactly the branch an ADMITTED
    # `--declare-only` skips. Every real admit therefore raised `UnboundLocalError` AFTER the pane
    # was already open: the seat came up, the command died, and the operator was left holding a
    # live pane the tool said nothing about.
    #
    # THE EMPTY LIST IS THE CORRECT VALUE, not a placeholder that silences a traceback. `blocked`
    # means "seats this command DECLINED to launch for an undeclared ending". On the admitted path
    # the command declined NOBODY — P2 made the launch set exactly the one named seat and the
    # admission launched it — so the undeclared-refusal contribution to the verdict is empty by
    # construction, and `launched`/`refused` below stay the counts they already meant.
    #
    # ⚠ WHY 16 GREEN ROWS MISSED IT, recorded so the next editor does not re-open the hole: every
    # 7.251 row that ADMITS ran `--dry-run`, and `cmd_launch` RETURNS at its dry-run branch above,
    # far short of the verdict block. The admitted REAL path was covered by nothing. The row that
    # closes that gap is `7.251 CRASH` in the self-test, which drives a real (non-dry-run) admit
    # all the way through this read — delete this binding and that row goes red.
    blocked = []
    if not _declare_only_admitted:
        undeclared = undeclared_endings(package_dir(args, register=False))
        blocked = [w for w in workers if w["agent"] in undeclared]
        if blocked:
            for w in blocked:
                print(c(f"  {w['agent']}: session `{undeclared[w['agent']]}` ENDED with an EMPTY "
                        f"disposition — NOT LAUNCHED", C_DEAD), file=sys.stderr)
            workers = [w for w in workers if w["agent"] not in undeclared]
            detail = (f"{len(blocked)} seat(s) above have an UNDECLARED ending: their last session "
                      f"ENDED and nobody declared how. Their work CONCLUDED — relaunching re-runs "
                      f"finished work, which is the harm.\nThis is a DEFECT FOR THE `leader` to "
                      f"investigate, NOT a relaunch instruction: only the occupant witnessed what "
                      f"its session meant, and no override flag expresses it — `--force` and "
                      f"`--force-memory` carry other gates and are barred from this one.\nThe "
                      f"`leader` has exactly one instrument for THIS class, and it does not "
                      f"override this verdict: `--declare-only <leader-anchor>` admits ONE named "
                      f"seat so that the session it opens can DECLARE THAT ENDING. (D42: the "
                      f"purpose is the caller's and the flag enforces nothing about it — what the "
                      f"flag decides is ADMISSION of the UNDECLARED class. It is NOT the door for "
                      f"a CRASHED seat: an `exited` row is re-run with `--rerun <leader-anchor>`.)"
                      f"\nSee: "
                      f"{coord_invocation(args)} ready-seats --explain <seat>")
            if not workers:
                refuse("state", detail + "\nNO pane was opened.", 1)
            print(c(detail, C_DEAD), file=sys.stderr)

    # 7.274 (A3): THE ADMISSION FILTER — `cmd_launch` CONSULTS THE DEPENDENCY GRAPH AT LAST.
    #
    # WHAT WAS BROKEN. This command read the `after` field zero times and called no readiness
    # computation, so `launch --only <seat>` walked straight past every term `ready-seats` had
    # already computed — a seat whose predecessors had not checked out, whose descriptor was gone,
    # whose store row the run had ruled held, all opened a pane exactly as if they were ready. The
    # 7.241 block above closed ONE of those classes (the undeclared ending). This closes the rest,
    # and it closes them the only way that adds no second home: by CALLING `ready_seat_rows` — the
    # one readiness home — and filtering on NAMED FIELDS OF ITS ROWS.
    #
    # ⚠ EXACTLY ONE CALL, AND NO ARITHMETIC. This block computes NO readiness of its own. It joins
    # `workers` (built from descriptor frontmatter, keyed `agent`) to the home's rows (built from
    # `taskforce.csv`, keyed `seat`) and evaluates a boolean over fields the home already emits. A
    # reconstruction here — looking each `after` member up among the other rows — is the PRIN-11
    # second-home defect AND is silently WRONG on a dangling predecessor, which gets no output row
    # of its own and would read as satisfied.
    #
    # ⚠ WHY HERE. Before PROP-8's validation, so that validates the set that will actually open;
    # BEFORE the returning `if args.dry_run:` branch, which is what makes dry-run parity true by
    # construction rather than by promise; AFTER the 7.241 block, which sets the flag clause I
    # reads. `ready_seat_rows` opens no pane and writes no surface, so it costs nothing here.
    #
    # ⚠⚠ AT `cmd_launch`'s OWN BODY DEPTH — NOT inside `if not _declare_only_admitted:` and NOT
    # inside `if blocked:`. The 7.241 anchor above sits two `If` suites deep; landing this block
    # there would disable it on exactly the path `--declare-only` admits. The self-test asserts the
    # placement at the AST, because the hazard is invisible to every behavioural row that does not
    # happen to admit.
    #
    # ⚠ TWO GATES RUN ABOVE THIS POINT AND SEE THE UNFILTERED SET, and they are deliberately not
    # moved: `launch_gates(…, len(workers) or 1, …)` sizes the MEMORY gate by seat COUNT and
    # `check_bindings` validates bindings. A launch of N seats of which N−1 defer is still
    # memory-gated at N. That over-reserves and never under-reserves — fail-safe in direction,
    # unfixable by placement, and out of this change's scope.
    _adm_rows = {r["seat"]: r for r in ready_seat_rows(args)}

    # ---- the filter: ADMIT(w), one row-level boolean, evaluated per worker -------------------
    #
    # ADMIT(w) == clause I  (`--declare-only` admitted, the landed sibling instrument)
    #          or clause I2 (D42: `--rerun` admitted — the crashed-row door. It is the SAME shape
    #                       as clause I and for the same reason: the boolean its own block already
    #                       set is CONSULTED here, never re-tested, so one act keeps one mechanism)
    #          or clause J  (no row joined — fail-OPEN where it is REACHED, and NAMED)
    # D12 (2026-08-20): clause I′ — the ruled-relaunch GRANT — is DELETED. A checked-out seat comes
    # back through the goal watcher's owed-work launch (`supervisor/reconcile.js`), which enqueues
    # directly and needs no authorization to mint, lose or latch.
    #          or the A–G conjunction over named row fields.
    #
    # ⚠ CLAUSE J IS SUPERSEDED WHERE THE REGISTRY HAS ROWS — `d-registry-refusal-supersedes-clause-j`
    # (OWNER RULING, 2026-08-10), superseding the `e0796b12` (2026-08-03) reading that clause J
    # fails open on EVERY launch. `check_bindings` (G-51 / 7.99) runs far above this filter and
    # REFUSES at exit 2 when the registry is NON-EMPTY and a launched seat has no `taskforce.csv`
    # row: that state is not a join gap, it is a lost record — a goal whose registry should carry
    # a row and does not is CORRUPT, which is precisely what the check exists to catch. The
    # owner's deciding invariant: *a seat cannot exist in `goal/` if there is no taskforce entry —
    # but in scaffolding it can exist even if not bound to any workflow.*
    #
    # SO CLAUSE J IS NOT DEAD, AND ITS SURVIVING SCOPE IS EXACTLY THE TWO STATES THE REFUSAL DOES
    # NOT REACH: an EMPTY registry (`check_bindings` opens `if not registry: return` — the legacy
    # `workers/` package and the scaffolding case, never in dispute), and `--force` (which WARNS
    # per seat and proceeds). Both are asserted: 7.99's no-registry row, and 7.274's clause-J rows.
    #
    # ⚠ CLAUSE J CARRIES NO INVOCATION-SHAPE CONDITION AND MUST NOT ACQUIRE ONE — not an `--only`
    # cardinality, not the exit-1 flag, not any other property of how the launch was typed. Nor
    # does the refusal above it: the supersession is keyed on the REGISTRY's state, never on how
    # the launch was typed. Where clause J IS reached, deferring would mint a launch outage out of
    # a join gap, which is the wrong fail direction: the same direction this file already refuses
    # for a degraded sensor.
    #
    # ⚠ CLAUSE I′ IS SCOPED TO THE GRANT ROW'S OWN `seat` CELL, which is what makes the admitted
    # set exactly one seat — not any cardinality of `--only`. P2b already refuses a second name;
    # this is the narrower statement of the same bound, and it is the one the design names.
    _adm_deferred = []
    _adm_kept = []
    for w in workers:
        _adm_row = _adm_rows.get(w["agent"])
        if (_declare_only_admitted or _rerun_admitted or _reopen_admitted or _adm_row is None
                or conjunction_admits(_adm_row)):
            _adm_kept.append(w)
            # THE TWO ADMITTED DISCLOSURES. An admission nobody can see is the same defect as a
            # silent filter, facing the other way — so both print, on STDOUT with C_HINT.
            if _adm_row is None:
                print(c(f"  {w['agent']}: ADMITTED WITHOUT A READINESS TERM — no `taskforce.csv` "
                        f"row joins this seat, so no term of the admission predicate could be "
                        f"evaluated for it. Admitting is the deliberate fail-OPEN direction: "
                        f"deferring would turn a join gap into a launch outage.", C_HINT))
            elif not (_declare_only_admitted or _rerun_admitted or _reopen_admitted):
                # 7.280 (O3) · S-2 — THE ORDINARY ADMISSION, AND IT IS THE CASE NOBODY TESTS.
                # Every other outcome at this door already speaks: three disclosures for the
                # instrument and clause-J paths, one line per deferred seat, one refusal when the
                # set empties. The seat admitted by the plain A–G conjunction was the ONE outcome
                # that printed nothing — and silence on success is exactly the shape a reader
                # ASSUMES is correct and never checks. "Never filter silently" and "never admit
                # silently" are the same bar facing two directions.
                #
                # ⚠ THE VERDICT IS PRINTED HERE AND DECIDES NOTHING HERE. This is the REPORT axis:
                # the admission was already taken, by `conjunction_admits` over named row FIELDS.
                # Row O below asserts that separation at the AST — every `verdict` read in this
                # whole block must sit inside a `print(...)`, so a verdict-keyed DECISION goes RED
                # while a verdict-carrying REPORT does not. Reverse the causation — admit because
                # the verdict reads `READY` — and the three ruled-legitimate relaunch lanes, none
                # of which can ever carry `READY`, become unadmissible by construction.
                #
                # ⚠ CLAUSE I's CARVE-OUT IS CONSULTED, NOT RE-TESTED. `_declare_only_admitted` is
                # the boolean the landed `--declare-only` block already set at its own admission;
                # this branch READS it for ONE purpose — to stay quiet where that block ALREADY
                # printed its own ADMITTED line and its trail. Re-printing would state the same
                # admission twice under two different sentences, which is how one act acquires a
                # second mechanism. Nothing here re-runs P2–P4, and nothing here mints.
                print(c(f"  {w['agent']}: ADMITTED — verdict {_adm_row['verdict']}; "
                        f"{_adm_row['reason']}", C_HINT))
        else:
            _adm_deferred.append((w, deferral_class(_adm_row), _adm_row))
    # NEVER FILTER SILENTLY: every deferred seat is named, with its class AND the field value that
    # decided it. A filter that removes without saying what it removed and why is indistinguishable
    # from a filter that never ran.
    #
    # 7.280 (O3) · S-1 — the verdict and the reason join the SAME line, APPENDED behind the class
    # and the field value rather than reordered around them. The append is deliberate and it is the
    # smaller of two changes: the landed shape `<seat>: NOT LAUNCHED — <class> (<field> = <value>)`
    # is asserted as a LITERAL by two rows already in this suite (7.274's NEVER-FILTER-SILENTLY row
    # and F1's RED CONTROL), so reshaping the prefix would have reddened two rows outside this
    # change for a cosmetic gain, and a RED outside one's own new rows is a revert, not a push.
    # The reader gains what the design asked for — the home's own verdict and its own reason, on
    # the line that named the class — and every prior assertion about that line stays true.
    for _adm_w, _adm_cls, _adm_r in _adm_deferred:
        _adm_f, _adm_v = deferral_field(_adm_r)
        print(c(f"  {_adm_w['agent']}: NOT LAUNCHED — {_adm_cls} ({_adm_f} = {_adm_v!r}); "
                f"verdict {_adm_r['verdict']}; {_adm_r['reason']}",
                C_DEAD), file=sys.stderr)
    workers = _adm_kept
    if _adm_deferred:
        _adm_detail = (
            f"{len(_adm_deferred)} seat(s) above were DEFERRED by the launch-admission filter: "
            f"`{coord_invocation(args)} ready-seats` had already computed a term that says this "
            f"seat is not a launch candidate, and until now this command never read it.\nThe "
            f"class word says what to do: `unmet-predecessor` waits; `occupied` is already live; "
            f"`unbuilt` needs its descriptor materialized; `renewing`/`revived` belong to lanes "
            f"that own the row, and so does `finished`; `records-disagree`, `exit-unruled`, "
            f"`claimed-unverified`, `terminal-unenumerated` and `undeclared-ending` route to the "
            f"`leader`.\nNO OVERRIDE "
            f"FLAG CARRIES THIS: `--force` carries the ROLE gate and `--force-memory` the MEMORY "
            f"gate, and neither reaches here. A seat that must simply RUN AGAIN is the goal "
            f"watcher's business, not this door's: it relaunches a seat-written "
            f"`declared-incomplete` row BY NAME (D33(a)), and the LEADER resolves the rest of "
            f"`exited`, `unverified`, `incomplete` or no-disposition rows with a ruling — D33(b); "
            f"`rule-disposition` (the verb that recorded it) was deleted [T2-R12, T1-R9] and no "
            f"replacement ruling instrument is wired here yet. ⚠ `exit-unruled` HAS ITS OWN DOOR "
            f"SINCE D42: a seat whose harness DIED mid-task is re-run here, in ONE act, with "
            f"`--rerun <leader-anchor>` — an ordinary working session, no CLEAR first, and the "
            f"`exited` row left standing. `--declare-only <leader-anchor>` remains this door's "
            f"one-seat instrument for an UNDECLARED ending and is not a way back to WORK.\nSee: "
            f"{coord_invocation(args)} ready-seats --explain <seat>")
        if not workers:
            refuse("state", _adm_detail + "\nNO pane was opened.", 1)
        print(c(_adm_detail, C_DEAD), file=sys.stderr)

    # PROP-8 (tv-ux-review): validate EVERY seat's launch config BEFORE any pane opens. An
    # invalid model slug used to fail only at model-init, INSIDE each spawned pane — a whole
    # wave died before its first checkin, its panes holding memory until someone noticed.
    invalid = [(w, e) for w in workers for e in [validate_seat(w)] if e]
    if invalid and not args.dry_run:
        for w, e in invalid:
            print(f"  {w['agent']}: {e}\n    briefing: {w['briefing']}", file=sys.stderr)
        refuse(
            "state",
            f"{len(invalid)} seat(s) above carry an invalid harness/model — NO pane "
            f"was opened (not even for the valid seats). Fix the briefing frontmatter, then "
            f"relaunch the whole set.",
            1)

    # 7.274 (A3) — THE ONE EXIT-CODE FOLD, and it is computed HERE: above the returning
    # `if args.dry_run:` branch, so BOTH paths exit from it (`C-1`'s ruled cure, Option B).
    #
    # THE DEFECT IT CLOSES. The dry-run branch returns above the verdict block, which is where the
    # only non-zero exit for a partial launch lives. So a launch that deferred SOME seats and left
    # a non-empty remainder exited 1 on the real path and 0 under `--dry-run` — opposite answers to
    # a cadence sweep that reads the exit code and nothing else.
    #
    # SEEDED FROM EVERY REFUSAL THAT IS A PROPERTY OF THE REQUEST and visible on BOTH paths — at
    # this writing exactly two sources: this block's own deferred list, and PROP-8's invalid-config
    # set, which `--dry-run` already detects and PRINTS while exiting 0. A fold seeded from the
    # deferred list alone leaves a bad model slug — ordinary, not exotic — still answering
    # oppositely, which is the same defect by a second door.
    #
    # THE TEST FOR ANYTHING ADDED LATER, so the next editor does not have to guess: ask what the
    # refusing condition is a property OF. Of the launch REQUEST (the seats named, their rows,
    # their briefings) → it JOINS THIS FOLD. Of a PRECONDITION of the act the real path performs
    # and the dry run does not (no tmux to open panes in) → it stays real-path-only, because
    # folding it would make the command refuse the very thing its own refusal text recommends. Of
    # an OUTCOME of that act (a pane that fails to open) → irreducible, and it is the ONE named
    # residual divergence below. Silence is not a fourth option.
    #
    # ⚠ "BOTH PATHS EXIT FROM ONE FOLD" MEANS ONE COMPUTED VERDICT READ BY TWO EXIT INSTRUMENTS,
    # not one `sys.exit` statement — the two paths leave this function by different instruments.
    # The real path's instruments are PROP-8's own refusal (for the invalid half) and the verdict
    # block's `sys.exit(1)` (for the deferred half, seeded into `refused` below); the dry-run
    # path's is the exit inside its branch.
    #
    # THE ONE RESIDUAL DIVERGENCE, which no placement removes and which is NOT claimed away: a real
    # launch can fail to OPEN a pane and `--dry-run` opens none, so where a pane-open fails the
    # real path exits 1 and the dry run exits 0. It is ONE-SIDED — the real path's code is never
    # lower than the dry run's — and it is never caused by an admission decision.
    _adm_fold = ([w["agent"] for w, _c, _r in _adm_deferred]
                 + [w["agent"] for w, _e in invalid])

    # 7.278 (C3): THE CAPACITY TERM — `cap.agent_panes`'s FIRST machine consumer on any launch
    # path. Before this the cap existed only as a number in `budget.json` and an aggregate in
    # `budget.py census()`; NOTHING that opens a pane had ever read it (measured at this row's
    # start: `agent_panes` occurred ZERO times in this file).
    #
    # ⚠ WHY HERE, and every half of it is load-bearing (`capacity-admission-spec.md` §8.4):
    #   • AFTER A3's admission filter — the term sizes the ADMITTED set, never the unfiltered
    #     roster. Sizing by the roster would size the gate with seats the DAG has already refused.
    #   • AFTER PROP-8's `validate_seat` pre-flight — an invalid harness/model must still refuse
    #     the WHOLE set regardless of capacity. A capacity deferral must never hide a config
    #     defect by removing the seat that carries it.
    #   • AFTER `_adm_fold` is computed, and this is the one placement the spec did not name
    #     because the fold landed after it was written: the fold is the EXIT-1 set, and a capacity
    #     deferral EXITS 0 (§5.1 — it is a WAIT, not a refusal). Computing the fold first is what
    #     keeps the two apart; a capacity deferral must never reach `_adm_fold` or `refused`.
    #   • BEFORE the returning `if args.dry_run:` branch — §4.4's parity holds BY CONSTRUCTION,
    #     and there is deliberately NO `args.dry_run` test anywhere in this block.
    #   • BEFORE the launch loop — no pane opens against an unread census.
    #   • `launch_gates` at the top of this command is NEITHER MOVED NOR RE-SIZED. Limb M (the
    #     memory floor) was answered there, live from `budget.json`, and it STANDS. Re-deriving it
    #     into a count here would weaken the one gate that is currently the real protection.
    #
    # ⚠ THE CENSUS IS CALLED EXACTLY ONCE PER INVOCATION, before the first pane opens, and its one
    # reading bounds the WHOLE act. The reason is measurable, not stylistic: `state.json` is
    # written by the `team-monitor` sensor, so panes THIS act opens do not appear in it until the
    # sensor next runs. A mid-loop re-read would return the same `in_use`, hence the same
    # `headroom`, and the act would spend the same headroom twice.
    _cap_pkg = package_dir(args, register=False)
    _cap_c = None
    _cap_err = ""
    _cap_why = []          # the degrade reasons that fired, in the §3.1 read order
    _cap_virgin = False    # 7.406: set True ONLY inside the D1 (census-absent) branch below
    _cap_in_run_n = 0      # 7.555: the in-run `cross_goal` correction, set in the census branch
    # The module's own loader, exactly as `watch.py` already uses it. RECORDED, NOT HIDDEN: `_load`
    # carries a leading underscore, so this is a private-name coupling. It is nonetheless the ONE
    # loader in the repo; the alternative — a public loader in `budget.py` — would need C2, whose
    # contract is scoped to emitting A FIELD, which a loader is not.
    _cap_b, _cap_eb = budget_mod._load(os.path.join(str(_cap_pkg), "budget.json"), "budget.json")
    _cap_s, _cap_es = budget_mod._load(os.path.join(str(_cap_pkg), "state.json"), "state.json")
    # `_cap_eb` is NOT this term's refusal: the floor read at the launch gate already refused an
    # unreadable budget (§5 R1) before this block runs. `_cap_es` is D1.
    if _cap_es:
        _cap_err = _cap_es
    else:
        try:
            _cap_c = budget_mod.census(_cap_b or {}, _cap_s or {})
        except Exception as _cap_exc:            # noqa: BLE001 — a sensor fault DEGRADES, never
            _cap_err = (f"census raised {_cap_exc.__class__.__name__}: {_cap_exc}")   # refuses
    if _cap_c is None:
        _cap_why.append(f"the census could not be produced: {_cap_err}")            # D1
        _cap_stamp = f"no snapshot — {_cap_err}"
        # 7.406: VIRGIN vs MISSING SNAPSHOT, positively established, never guessed. `state.json`
        # ABSENT (never UNREADABLE — `_cap_marker_absent` answers True on a genuine
        # `FileNotFoundError` only, so a present-but-corrupt state.json leaves `_cap_virgin` False
        # exactly as `_cap_es`'s own ABSENT/UNREADABLE split would) AND no sensor has ever written
        # a durable artifact here AND no launch has ever completed here. Every marker read shares
        # `_cap_marker_absent`'s one failure direction: present, unreadable, or erroring all read
        # as "not absent", so `_cap_virgin` stays False rather than guessing.
        _cap_virgin = (
            _cap_marker_absent(os.path.join(str(_cap_pkg), "state.json"))
            and _cap_marker_absent(os.path.join(str(_cap_pkg), "coordination", "team-monitor.log"))
            and _cap_marker_absent(os.path.join(str(_cap_pkg), "coordination", "team-monitor.lock"))
            and _cap_marker_absent(os.path.join(str(_cap_pkg), "sessions.csv"))
        )
    else:
        # ---- THE FIVE DECISION FIELDS, READ BEFORE `headroom` IS USED AT ALL (§3.1/§3.2) -------
        #
        # ⚠ THE ORDER IS THE POINT, AND A SELFTEST ROW ASSERTS IT OVER THIS FUNCTION'S OWN SOURCE.
        # `headroom` is a confident-looking number that a stale, incomplete or in-run-`cross_goal`
        # census produces just as readily as a sound one. A consumer that reads it first has
        # already made its decision before it learns the reading was bad.
        _cap_verdict = _cap_c["verdict"]
        _cap_stale = _cap_c["stale"]
        _cap_complete = _cap_c["complete"]
        _cap_unclassified = _cap_c["unclassified"]
        _cap_cross = _cap_c["cross_goal"]
        # D5's predicate — THE TERM ON THE ROW, NEVER ON THE CLASS. A legitimate other-goal seat
        # and a same-run leak both land in `cross_goal` with the SAME class value, so no
        # enumeration over class membership separates them; the already-emitted `descriptor` field
        # does. `census()` cannot compute this at its own home — it receives two mappings and
        # never the run root — and giving it one would move a consumer's question into a reporter.
        _cap_seats_root = os.path.join(os.path.abspath(str(_cap_pkg)), "seats") + os.sep
        _cap_in_run, _cap_cross_out = [], []
        for _m in _cap_cross:
            (_cap_in_run
             if os.path.abspath(_m.get("descriptor") or "").startswith(_cap_seats_root)
             else _cap_cross_out).append(_m)
        _cap_in_run_n = len(_cap_in_run)
        # ⚠ IF SEVERAL FIRE, THE REASON NAMES ALL OF THEM. A line that named only the first would
        # be a filter that removed a reason without saying so.
        if _cap_verdict == "UNKNOWN":                                              # D2
            _cap_why.append("census verdict UNKNOWN")
        if _cap_stale is True:                                                     # D3
            _cap_why.append("census reports stale=true")
        # D2 and D3 OVERLAP today (`stale` forces `UNKNOWN` inside `census()`). They are tested
        # separately ON PURPOSE: they are two different facts, `budget.json`'s own `bars.staleness`
        # names the second, and a consumer that folded them could not survive the day one stops
        # implying the other.
        if _cap_complete is False or _cap_unclassified:                            # D4
            _cap_why.append(f"census reports complete=false "
                            f"({len(_cap_unclassified)} unclassified row(s))")
        # 7.555: D5 IS NOW A CORRECTION, NOT A DEGRADE — and the reason it degraded is the reason
        # it must not. `census()` files a live agent pane with `agent_type_source: no-seat` under
        # `budget.py`'s rule 3, and rule 3 asks only whether SOME goal declares it; when the answer
        # comes back as a descriptor inside THIS run's own `seats/`, the row is not another goal's
        # seat "accounted elsewhere" (`budget.py`'s cross_goal ruling) — it is OUR OWN seat whose
        # harness is live and which HAS NOT CHECKED IN YET. That state is entered by every launch
        # and left ONLY at the seat's own `cmd_checkin`, which is what writes the roster pane the
        # sensor resolves a seat name from. So the degrade NEVER CLEARED for a harness that is live
        # and never checks in — an agent parked on a permission prompt, or one ignoring the
        # protocol — while a DEAD one cleared at once through `census()`'s own `if not live`. One
        # such pane pinned the whole room in CAP NOT CONSULTED indefinitely, with only the memory
        # floor bounding it (the residual F2 of task 7.552's certified review).
        #
        # ⚠ THE READING WAS NEVER AMBIGUOUS, WHICH IS WHY THIS CORRECTS RATHER THAN DISTRUSTS. D5's
        # own degrade reason already said precisely what was wrong and by how much — "`in_use`
        # under-counts and headroom over-admits" — and a term that can NAME its error exactly can
        # SUBTRACT it. Degrading on a knowable miscount discards a sound number to avoid a
        # correctable one, and here it discarded the cap for the whole room rather than for the
        # act. The rows are counted below, at the ONE place `headroom` is used.
        #
        # ⚠ AND IT STAYS THE TERM ON THE **ROW**, NEVER ON THE CLASS. `_cap_cross_out` — a
        # `cross_goal` pane resolving OUTSIDE this run — is untouched and still spends no slot
        # (N2); only the in-run rows are counted. `census()` cannot make this split at its own home
        # (it receives two mappings and never the run root), which is why the correction lives with
        # the consumer that owns that root, exactly where the predicate already did.
        _cap_age = _cap_c["snapshot_age_s"]
        _cap_stamp = (f"snapshot age {_cap_age}s (stale after {_cap_c['stale_after_s']}s)"
                      if _cap_age is not None
                      else "snapshot age unknown — state.json carries no captured_at")
    _cap_deferred = []
    # COUNTED — membership read out of `budget.json` at runtime, the SAME predicate `census()`
    # classifies on, so the act and the census can never disagree about who spends a slot. The
    # parked owner door is outside it because `budget.json` says so by name — this POINTS at that
    # exclusion and MINTS none. 7.363 hoisted it above the branch: BOTH the census-failure branch
    # and the full-capacity branch decide on it, and computing it twice would be a second home.
    _cap_counts = set((_cap_b or {}).get("counting", {}).get("counts_toward_cap") or [])
    # 7.406: THE EMPTY-ROOM BOUND, read from the SAME `_cap_b` load above — never a second home.
    # An undeclared or non-numeric `cap.agent_panes` cannot bound an admission, so it keeps
    # `_cap_virgin`'s reading from being usable rather than inventing a number: the branch below
    # falls back to the byte-for-byte existing defer, exactly as an ordinary D1 does.
    _cap_agent_panes = (_cap_b or {}).get("cap", {}).get("agent_panes")
    _cap_coldstart = (_cap_virgin and isinstance(_cap_agent_panes, int)
                      and not isinstance(_cap_agent_panes, bool) and _cap_agent_panes >= 0)
    # 7.363 (F19): IS THE ROOM COUNTABLE AT ALL? Written on the two readings that mean the census
    # DESCRIBES NOTHING — it could not be produced (D1), or its snapshot is too old to describe the
    # room now (D3, which also forces `verdict: UNKNOWN` inside `census()` today). It is
    # deliberately NOT `_cap_why`: D4 and D5 are IMPERFECT readings, not absent ones — the census
    # produced a number there and 7.278's degrade still owns them — and an UNDECLARED
    # `cap.agent_panes` is a `budget.json` configuration gap, not a census failure, so it degrades
    # too. Reading `_cap_stale` rather than re-deriving it keeps the ruled read order intact.
    _cap_blind = _cap_c is None or _cap_stale is True
    if _cap_blind:
        if _cap_coldstart:
            # ---- THE COLD-START BRANCH — ADMITS ON THE EMPTY-ROOM BOUND, NEVER MORE -----------
            #
            # 7.406. `_cap_virgin` is positively established (above) on markers this same package
            # carries, never guessed; a room nothing has ever observed has an accurate census of
            # its own — in_use 0 — and this branch admits exactly that reading, sourced from the
            # SAME `_cap_b` load every other branch reads `cap.agent_panes` from. Overflow beyond
            # the bound still WAITS, in the same never-filter-silently shape every other branch
            # here is held to.
            print(c(CAPACITY_COLDSTART_LINE.format(pkg=str(_cap_pkg)), C_HINT))
            _cap_final, _cap_deferred, _cap_taken = _cap_admit_upto(workers, _cap_counts,
                                                                    _cap_agent_panes)
            workers = _cap_final
            for w in _cap_deferred:
                print(c(CAPACITY_DEFER_LINE.format(agent=w["agent"], k=_cap_taken,
                                                   m=_cap_taken + len(_cap_deferred)), C_DEAD))
        else:
            # ---- THE CENSUS-FAILURE BRANCH — IT DEFERS, AND IT STILL NEVER REFUSES -------------
            #
            # G-2335's answer. The room cannot count itself, so `headroom` is UNKNOWN — not zero,
            # not large — and admitting a counted seat here is admitting blind. Every counted
            # candidate WAITS. What keeps this an enforcement and not an outage is the pickup lane
            # printed with it: the cadence sweep re-admits with no further act once a census
            # source exists again. Uncounted seats (the owner door, a descriptor
            # declaring no type) still proceed — `budget.json` says they spend no slot, so nothing
            # about the cap bears on them, and blocking them would be enforcing a term they were
            # never under. The exit code is untouched: a WAIT is not a failure.
            print(c(CAPACITY_UNENFORCEABLE_LINE.format(reason="; ".join(_cap_why), stamp=_cap_stamp,
                                                       pkg=str(_cap_pkg)), C_HINT))
            _cap_final = []
            for w in workers:
                if (w.get("agent_type") or "") in _cap_counts:
                    _cap_deferred.append(w)
                else:
                    _cap_final.append(w)
            workers = _cap_final
            # NEVER FILTER SILENTLY — the same bar the full-capacity branch is held to.
            for w in _cap_deferred:
                print(c(CAPACITY_CENSUS_DEFER_LINE.format(agent=w["agent"]), C_DEAD),
                      file=sys.stderr)
    elif _cap_why:
        # ---- THE DEGRADE BRANCH — IT NEVER REFUSES -------------------------------------------
        #
        # An IMPERFECT census reading degrades — since 7.363 this branch owns D4 and D5 only, the
        # two readings where the census DID produce a number and the number is merely untrustworthy
        # in a named direction, plus an undeclared cap. Refusing on one would mint a LAUNCH OUTAGE
        # out of a SENSOR OUTAGE, which is the wrong fail direction. (The readings where the census
        # describes NOTHING no longer arrive here at all: they take the branch above and DEFER.)
        # `headroom` is not read, no allowance is
        # computed, every admitted seat proceeds, and the act NAMES on its own output that the cap
        # was not consulted, with every reason that fired and the snapshot stamp. Limb M — the
        # memory floor, read live at the launch gate — stands as the only capacity protection, and
        # the exit code is untouched: a degrade is not a failure.
        print(c(CAPACITY_DEGRADE_LINE.format(reason="; ".join(_cap_why), n=len(workers),
                                             stamp=_cap_stamp), C_HINT))
    else:
        # ---- THE FULL-CAPACITY BRANCH — `headroom` IS USED ONLY FROM HERE ---------------------
        #
        # The allowance reads the EMITTED `headroom` and never `cap` or `in_use` directly:
        # combining those two is `census()`'s job, and doing it here would be a second home for
        # one fact. BREACH is a CONFIDENT reading, not a degraded one, so it takes THIS branch —
        # never the degrade one — and defers every counted candidate. `max(0, …)` normalizes the
        # allowance to a count; it is NOT what produces that deferral, and is not claimed to be:
        # the loop's own `_cap_taken < _cap_allow` already defers everything on a negative value.
        # 7.555: the EMITTED `headroom`, less the in-run `cross_goal` rows `census()` left out of
        # `in_use` (D5, above). This is NOT the recombination `cap` + `in_use` that 7.278 bars and
        # a selftest row asserts the absence of — neither field is read here; it is the consumer
        # applying a correction only the consumer can compute, to the one number it is allowed to
        # read. `_cap_in_run_n` is 0 on every ordinary room, so this is a no-op the instant every
        # seat has checked in — which is exactly the transient regime 7.552's review measured and
        # this row must not over-correct into a permanent refusal.
        _cap_allow = max(0, _cap_c["headroom"] - _cap_in_run_n)
        if _cap_verdict == "BREACH":
            print(c(CAPACITY_NOTE_BREACH, C_HINT))                                 # N3
        if _cap_c["unaccounted"]:                                                  # N1
            print(c(CAPACITY_NOTE_UNACCOUNTED.format(k=len(_cap_c["unaccounted"])), C_HINT))
        if _cap_in_run:                                                            # D5 (7.555)
            print(c(CAPACITY_NOTE_IN_RUN.format(k=_cap_in_run_n), C_HINT))
        if _cap_cross_out:                                                         # N2
            print(c(CAPACITY_NOTE_CROSS_GOAL.format(k=len(_cap_cross_out)), C_HINT))
        # COUNTED — the subsequence of ADMITTED, IN ADMITTED'S OWN ORDER, whose DECLARED
        # `agent_type` is a member of `counting.counts_toward_cap` (`_cap_counts`, read once above
        # the branch since 7.363 — both branches decide on it).
        # ⚠ NO ORDERING IS MINTED. `ADMITTED_FINAL` preserves A3's order exactly: no priority, no
        # reordering, no queue. Consequence, stated rather than left to be discovered: a
        # short-lived unblocking launch can be deferred behind long-running work. That is a WAIT
        # that clears as panes free; an ordering would be a `leader` ruling and a separate row.
        _cap_taken = 0
        _cap_final = []
        for w in workers:
            _cap_atype = w.get("agent_type") or ""
            if _cap_atype in _cap_counts:
                if _cap_taken < _cap_allow:
                    _cap_taken += 1
                    _cap_final.append(w)
                else:
                    _cap_deferred.append(w)
            else:
                _cap_final.append(w)
                if not _cap_atype:
                    print(c(CAPACITY_NOTE_UNDECLARED.format(agent=w["agent"]), C_HINT))
        workers = _cap_final
        # NEVER FILTER SILENTLY: every capacity-deferred seat is named, with how many of the
        # counted candidates were admitted. A filter that removes without saying what it removed
        # and why is indistinguishable from a filter that never ran.
        for w in _cap_deferred:
            print(c(CAPACITY_DEFER_LINE.format(agent=w["agent"], k=_cap_taken,
                                               m=_cap_taken + len(_cap_deferred)), C_DEAD),
                  file=sys.stderr)
        # ⚠ AND WHEN THE TERM EMPTIES THE SET IT STILL DOES NOT REFUSE (§5.1). The act opens no
        # pane, names every deferral, and EXITS 0 — so the output has to carry the fact the exit
        # code no longer carries. This is DERIVED, not chosen: this row's contract closes the
        # refuse branch at ONE case (the floor unreadable at the instant of use), so calling
        # `refuse()` here is unavailable — and it is also the honest reading, because an exit code
        # that reads as a refusal makes a WAIT indistinguishable from a DENIAL.
        if _cap_deferred and not workers:
            print(c(CAPACITY_EMPTY_LINE, C_DEAD), file=sys.stderr)

    target = os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")
    # 7.362 (F18, G-m4-demo-workflow-registrar-0803-2307): a DAEMON-FIRED exec holds NEITHER
    # variable — `runToolLikeExec` passes `envFile: null`, so the exec inherits only the systemd
    # user manager's environment, measured to contain neither (`systemctl --user
    # show-environment` -> 0 matches; a real transient unit printed both UNSET). `--tmux-target`
    # is that exec's only way to name a target, and it is an INPUT to the refusal below, never a
    # weakening of it: an absent or empty flag leaves `target` exactly as the two variables left
    # it, and the same refusal fires. THE EMPTY-TARGET DEFAULT IS NEVER WIDENED — tmux resolves
    # an empty target to the MOST RECENT session (measured: the LIVE room), which is what this
    # refusal exists to prevent, so the assignment below is GUARDED on a non-empty value and must
    # never become an unconditional `target = args.tmux_target`.
    #
    # ⚠ THE LINE ABOVE IS AN ANCHOR: `7.278`'s static rows slice `cmd_launch`'s own source at the
    # literal `target = os.environ.get("COORD_LAUNCH_TARGET")`. Everything this row adds sits
    # AFTER it, so that slice is byte-identical to what those rows already measure.
    _f18_explicit = str(getattr(args, "tmux_target", "") or "").strip()
    if _f18_explicit:
        target = _f18_explicit
    # ==== E22 — THE LANE BRANCH: the COMPOSER moves, the admission does not. Placed AFTER every
    # admission wall and the capacity term, and BEFORE the tmux-environment refusal below: a caged
    # leader has no $TMUX_PANE and must not be refused for lacking a window it will not open. The
    # door the leader used (`--rerun` / `--declare-only` / `--reopen` / a plain launch) and its
    # anchor become the daemon door's brake reason. See the block comment on `launch_daemon_lane`.
    if _lane == "daemon":
        _lane_door, _lane_why = (("rerun", _rerun_anchor) if _rerun_admitted
                                 else ("declare-only", _decl_anchor) if _declare_only_admitted
                                 else ("reopen", _reopen_reason) if _reopen_admitted
                                 else ("launch", ""))
        launch_daemon_lane(args, workers, package_dir(args, register=False), _adm_fold, blocked,
                           _adm_deferred, _lane_door, _lane_why,
                           reopen_downstream=_reopen_downstream)
        return
    if not target and not args.dry_run:
        refuse(
            "environment",
            "launch opens tmux panes and this shell is not inside tmux (no $TMUX_PANE),"
            " so there is no window to open them in.\nRun it from leader's tmux pane, pass"
            " --tmux-target <pane-or-window-id> (what a daemon-fired exec does: it inherits no"
            " tmux environment at all), or use --dry-run to see the commands it would run.",
            1)
    if _f18_explicit and not args.dry_run:
        # The carriage has to be OBSERVABLE, or a capture cannot tell a resolved target from a
        # refusal that never fired. Printed only when the flag supplied it: an env-resolved
        # launch prints exactly what it printed before.
        print(c(f"tmux target: {target} (from --tmux-target; the environment carried none)",
                C_HINT), file=sys.stderr)

    if args.dry_run:
        for cwd in dict.fromkeys(w["cwd"] for w in workers
                                 if w["harness"] != "claude" and w["cwd"]):
            print(f"[dry-run] would refresh the worker mirror for {cwd}")
        for w in workers:
            verr = validate_seat(w)  # PROP-8: the dry-run shows the same pre-flight refusal
            # The real spawn reads its prompt from a file (G-11); show that shape, not an inlined
            # prompt the launcher would never actually type.
            cmd, err = (None, verr) if verr else harness_command(
                w, prompt_path=(base_dir(args) / "prompts" / f"{w['agent']}-<stamp>.txt"))
            kind, wname = seat_placement(w)
            place = {"own": "window", "shared": f"window:{wname}"}.get(kind, "pane")
            print(f"[dry-run] {w['agent']} ({w['harness']}/{w['model'] or 'plan-default'}"
                  f"{'/' + w['effort'] if w['harness'] == 'claude' else ''}, {place}, cwd={w['cwd']}): "
                  f"{cmd if cmd else 'REFUSED — ' + err}")
        # 7.274 (A3): the dry run's exit instrument, reading the ONE fold computed above. Before
        # this the branch returned 0 unconditionally and the real path exited 1 on the same set.
        if _adm_fold:
            print(c(f"launch INCOMPLETE (dry-run): {len(_adm_fold)} seat(s) would NOT launch "
                    f"({', '.join(_adm_fold)}). The exit code is the same one a real launch of "
                    f"this set would return — a dry run exists to show what a real launch would "
                    f"do, and one that answered 0 where the real path answers 1 would make the "
                    f"one command meant for inspection the one that lies.", C_DEAD),
                  file=sys.stderr)
            sys.exit(1)
        return

    # The memory gate is answered UP FRONT by `launch_gates` (no role gate anymore
    # [T2-R10, D24, F-simplicity-7]).

    # BEFORE any seat boots: a worker reads its rules once, at startup, so a refresh that lands
    # after the pane opens is a refresh the worker never sees.
    refresh_mirrors_for(workers)

    tmux_raise_history_limit()  # exports capture full scrollback (see export-transcript)
    refused, indeterminate = [], []
    for w in workers:
        pane, err = launch_seat(w, args, target, strict_liveness=True)
        kind, wname = seat_placement(w)
        place = {"own": "window", "shared": f"window:{wname}"}.get(kind, "pane")
        label = f"{w['agent']} ({w['harness']}/{w['model'] or 'plan-default'}, {place})"
        if err:
            # 7.567: a seat this host could not OBSERVE is not a refused seat. Both are counted
            # out of `launched` — neither was seen up — but only a refusal is a positive finding.
            (indeterminate if err.startswith(HARNESS_UP_UNVERIFIABLE) else refused).append(w["agent"])
            print(f"  {label}: FAILED — {err}", file=sys.stderr)
        else:
            print(f"launched {label} in {pane}"
                  + (" (session /rename scheduled)" if w["harness"] == "claude" else ""))

    # D54/D66/D72 — WRITE THE REASON, on the seat's freshly-opened row, AFTER the real launch.
    #
    # ⚠ GATED ON A REAL OPEN ROW, NOT ON `_reopen_admitted` ALONE. Admission can be TRUE while no
    # pane ever opened for the reopened seat — the capacity gate (§ above, `_cap_deferred`) can
    # defer an admitted seat AFTER this block's own admission ran and BEFORE `launch_seat` is ever
    # called. `sessions_open_ids` answers "did a new OPEN row actually land for this seat", which
    # is the only question that matters here: if it did not, there is nothing to write, and
    # writing to the seat's LAST row in that case would silently touch the `done` row `--reopen`
    # is built to leave untouched — exactly the wrong-shape mutation D54 forbids.
    if _reopen_admitted:
        _ro_new_sid = sessions_open_ids(_ro_pkg).get(_rot, "")
        if _ro_new_sid:
            _ro_msg_num = None
            if _reopen_downstream:
                # D72's chosen durable home for the WALK-FORWARD FLAG is `messages.md`, not a
                # second `sessions.csv` column: the list is unbounded in length (any number of
                # downstream seats), `messages.md` is ALREADY the append-only bus every seat and
                # the leader read routinely ("where the goal's readers will see it"), and a
                # sessions.csv cell is sized for short strings (every existing column is an
                # id/anchor/word, never a list) — widening that convention for one column would
                # be the "new pattern, not a continuation of one" the mechanism lane warned about.
                # The reason CELL still POINTS at the note (below), so a reader of the row alone
                # is never left with a dangling reference.
                _ro_msg_num = append_message(
                    base_dir(args), DISPOSITION_WRITER_KIT, "leader", "note",
                    f"reopen: `{_rot}` was re-opened (session `{_ro_new_sid}`, reason "
                    f"`{_reopen_reason}`) on top of a `done` row that "
                    f"{len(_reopen_downstream)} seat(s) already ran depending on: "
                    f"{', '.join(_reopen_downstream)}. Their work is NOT rolled back or "
                    f"re-blocked — this is a flag, not an undo (D54/D72).")
            _ro_reason_cell = _reopen_reason
            if _ro_msg_num is not None:
                _ro_reason_cell += f" (downstream flagged in messages.md #{_ro_msg_num})"
            with coord_lock(base_dir(args)):
                _ro_path = sessions_csv(_ro_pkg)
                _ro_header, _ro_rows = read_csv_table(_ro_path, SESSIONS_COLS)
                _ro_header, _ro_widened = widen_header(_ro_header, SESSIONS_COLS)
                if _ro_widened:
                    _ro_rows = [pad_row(r, _ro_header) for r in _ro_rows]
                _ro_idx = {c: i for i, c in enumerate(_ro_header)}
                # LAST row for this session-id — never "last row for the seat": the seat's LAST
                # row is not necessarily THIS session if something else raced the append, and a
                # row found by seat name alone could resolve to the `done` row itself if the new
                # open row somehow failed to land between the check above and this lock.
                _ro_target = None
                if "session-id" in _ro_idx:
                    for r in _ro_rows:
                        pad_row(r, _ro_header)
                        if r[_ro_idx["session-id"]].strip() == _ro_new_sid:
                            _ro_target = r
                if _ro_target is not None and REOPEN_REASON_COL in _ro_idx:
                    _ro_target[_ro_idx[REOPEN_REASON_COL]] = _ro_reason_cell
                    write_csv_table(_ro_path, _ro_header, _ro_rows)
                    print(c(f"  {_rot}: sessions.csv `{REOPEN_REASON_COL}` recorded on session "
                            f"`{_ro_new_sid}`.", C_HINT))
                else:
                    print(c(f"  WARNING {_rot}: the reopen reason could NOT be written — no open "
                            f"row `{_ro_new_sid}` was found to carry it. The launch itself "
                            f"succeeded; only the durable reason record is missing.", C_DEAD),
                          file=sys.stderr)

    # ---- the launch's VERDICT (leader ruling, exit-code semantics) -------------------------
    #
    # Every PRE-SPAWN refusal in this command — PROP-8, the role gate, the memory gate — already
    # exits 1, and `close-seat --renew` exits 1 when its launch_seat fails. This per-seat loop was
    # the ONE path that printed `FAILED` and exited 0, so a launch in which every seat was refused
    # reported SUCCESS to anything reading the status. Making the path consistent with the command
    # it lives in, not new policy.
    #
    # SUCCESSES ARE KEPT — no rollback. A partially-launched wave is a real state and tearing down
    # working seats to make the exit code tidy would cost more than the defect.
    #
    # ⚠ THE COUNTS ARE NOT DECORATION: an exit code cannot distinguish PARTIAL from TOTAL failure,
    # and that difference decides what the operator does next (relaunch two seats, or find out why
    # nothing came up). The code says "something failed"; only this line says how much.
    launched = len(workers) - len(refused) - len(indeterminate)
    # 7.241: the UNDECLARED-ending seats join the refusal AFTER `launched` is computed, never
    # before — they were filtered OUT of `workers`, so seeding them into `refused` would subtract
    # them from a total they were never in and undercount the seats that actually came up. They
    # belong in the verdict because they ARE refusals of this command in the sense it already
    # means: a mass launch that deliberately skipped one must exit 1 and say `launch INCOMPLETE`.
    # A scripted caller — the cadence sweep — reads the exit code and nothing else, so omitting
    # them would report SUCCESS for a launch this command declined to perform, which is the same
    # defect this verdict block was written to fix arriving by a new door.
    # 7.274 (A3): the admission-DEFERRED seats join the refusal on exactly 7.241's own ground and
    # at exactly its position — AFTER `launched` is computed, because they were filtered OUT of
    # `workers` and seeding them earlier would subtract them from a total they were never in. They
    # are the real-path half of the ONE fold computed above the dry-run branch: the same set, read
    # by this path's own exit instrument, which is what makes the two paths' exit codes agree.
    refused = refused + [w["agent"] for w in blocked] \
        + [w["agent"] for w, _c, _r in _adm_deferred]
    # 7.567 PRECEDENCE — refusal outranks indeterminacy. A refusal is a POSITIVE observation that
    # a seat did not come up; an indeterminate outcome only says this host could not look. A run
    # carrying both has a KNOWN failure in it and must exit 1, with the indeterminate seats named
    # in the line above rather than hidden behind the weaker code. Exit EXIT_INDETERMINATE only
    # when nothing was positively refused and something could not be observed.
    if indeterminate:
        print(c(f"launch INDETERMINATE for {len(indeterminate)} seat(s) "
                f"({', '.join(indeterminate)}): this host could not observe whether their harness "
                f"came up — the per-seat reason is above. NOT counted as launched, and NOT a "
                f"refusal: check them by hand before treating them either way.",
                C_DEAD), file=sys.stderr)
    if refused:
        print(c(f"launch INCOMPLETE: {launched} launched, {len(refused)} refused "
                f"({', '.join(refused)}). The launched seats are UP and were not rolled back.",
                C_DEAD), file=sys.stderr)
        # ⚠ AND THE NEXT-HINT IS ITSELF PART OF THE DEFECT: "every seat above must appear there"
        # is false the moment one was refused, and a reader who checks `workers` and finds the
        # refused seat missing would read the tool's own instruction as evidence something ELSE
        # broke. Fixing the exit code and leaving this sentence unqualified MOVES the lie.
        print(c(f"next: {coord_invocation(args)} workers — the {launched} LAUNCHED seat(s) must "
                f"appear there; the {len(refused)} refused one(s) will not, and that is this "
                f"command's own result, not a second failure", C_HINT))
        sys.exit(1)
    if indeterminate:
        sys.exit(EXIT_INDETERMINATE)
    print(c(f"next: {coord_invocation(args)} workers — every seat above must appear there; one "
            f"that never checks in never booted", C_HINT))
