# ---------- dag-10: the ready-SEAT arithmetic (`coordinate ready-seats`) ----------
#
# The ruling this realizes (`d-advancement-on-checkout`): the whole workflow's seat rows are
# registered at materialization, and A SEAT IS READY WHEN EVERY `after` PREDECESSOR HAS A CLEAN
# CHECK-OUT WITH DISPOSITION `done`. This is CMP-25's fast path emulated in a CLI with no
# long-lived driver — THE CALLER HOLDS NO LIST; it recomputes from disk every sweep. That is the
# whole reason this is a command and not a daemon: a cached frontier is a second copy of run
# state, and run state is DERIVED (the KG is explicit that `taskforce.csv` carries no status
# column).
#
# WHY IT LIVES IN `coord.py` and not in a sibling script: the computation reads `workers.md`,
# `awaiting-close.json` and `sessions.csv` through `load_workers`, `current_row`, `load_awaiting`
# and `session_disposition` — all four of them here. A sibling would re-implement all four, which
# is the two-surfaces re-derivation hazard this module names in half a dozen places. Inside, it
# also earns the `save-coord.py` gate and its self-test rows for free.
#
# ⚠ IT LAUNCHES NOTHING, WRITES NOTHING, MESSAGES NOBODY. It is a pure read whose output another
# actor acts on.

def taskforce_after(pkg):
    """{seat: [predecessors]} from the run's `taskforce.csv`, in FILE ORDER. `{}` when absent.

    The `after` cell is COMMA-separated, parsed exactly as `materialize-seats.py` WRITES it
    (`preds = [p.strip() for p in raw.split(",") if p.strip()]`). One producer, one parse — a
    reader that invented its own separator would silently see one predecessor named
    "a,b" and mark a seat ready that has two unfinished parents.

    ⚠ 7.424 (W1): EACH MEMBER IS AN `AfterMember`, WHICH IS THE RAW TOKEN AND CARRIES ITS
    DECOMPOSITION. This function is the SOLE producer of the run's `after` members, and it is
    where the member grammar is decomposed — by delegating to `parse_after_member`, which holds
    the ONLY decomposition of that grammar in this module. Before this, `taskforce_after` handed
    out RAW tokens and `parse_after_member` sat beside it as a second reading a consumer had to
    know to ask for: every consumer that did not (`edge-runner-job.py`, `run-state-job.py`,
    `watch.py`) saw a guarded member as a literal seat name. The two readings are now one, and a
    consumer cannot obtain a member that has not been through it."""
    header, rows = read_csv_table(pkg / "taskforce.csv", [])
    if not rows or "seat" not in header:
        return {}
    idx = {c: i for i, c in enumerate(header)}
    out = {}
    for r in rows:
        pad_row(r, header)
        seat = r[idx["seat"]].strip()
        if not seat:
            continue
        raw = r[idx["after"]].strip() if "after" in idx else ""
        # 7.424: the comma split is unchanged — the CELL grammar. Each member it yields is then
        # handed to the one MEMBER-grammar reading (`AfterMember` -> `parse_after_member`, both
        # defined below; resolved at call time). The token itself is untouched: `AfterMember` IS
        # the string, so every consumer's comparison, lookup, join and rendering is byte-identical.
        out[seat] = [AfterMember(p.strip()) for p in raw.split(",") if p.strip()]
    return out


# ---------- 7.383: the GUARDED `after` MEMBER — its parse, its values, its key ----------
#
# THE DEFECT THIS CLOSES, measured before the fix and not inferred. A guarded dependency is written
# into `taskforce.csv` as `<seat>[<key>=<value>]` — the materializer writes it and
# `p-materializer-guard-suffix` rules the shape legal. The readiness loop then handed that WHOLE
# STRING to `terminal_disposition` as a seat name. Nothing stripped the bracket, so the lookup was
# for a seat that cannot exist, `None` came back, and the member rendered `<no check-out>`.
# CATEGORICALLY: every guarded edge in every run was permanently unmet no matter what its
# predecessor did. The control: the leader ruled K3's disposition `done` and the edge still read
# `<no check-out>` — a roster problem clears on that, a name-lookup problem cannot.
#
# ⚠ THE PARSE IS A MIRROR, NOT A SIBLING. `materialize-seats.py`'s `_manifest_after_ids` already
# reads this grammar, and its ONE non-obvious ordering property is load-bearing: bracketed content
# is removed BEFORE the alternate split, so a `|` INSIDE a guard value never reads as an alternate
# (`check_acyclic`'s #3386 strip-then-split defect is what happens when the two are ordered the
# other way). This function reproduces that order deliberately. Two homes for one grammar is the
# defect class that BORE this bug; they are kept in step by that order and by the self-test row
# that drives both.
#
# ⚠ A GUARD NEVER AUTO-SATISFIES. That single property is the whole blast-radius argument for
# changing a term every run's readiness arithmetic reads: no row whose guard is genuinely
# unsatisfied can be admitted by this change, because admission requires a RECORDED RULING, and a
# row that has none stays BLOCKED with a guard-honest reason instead of the name-lookup lie.
# Stripping the bracket WITHOUT evaluating the guard would have been the smaller diff and would
# have silently admitted exactly those rows.

# The guarded-member grammar: `name[key=value]`, ONE trailing bracket group. `value` admits `|`
# because the alternate test below runs on the BRACKET-STRIPPED text — a `|` that survives to here
# is inside a guard value and is not an alternate. A bracketed token that does NOT match this
# grammar (`name[nokey]`, a second group) is NOT a guarded member and falls to the bare path, where
# it renders exactly as it does today: unmet, `<no check-out>`. That is the fail-safe direction —
# an unparseable guard must never become a satisfied one.
GUARDED_MEMBER_RE = re.compile(r"\A(?P<name>[^\[\]]+)\[(?P<key>[^\[\]=]+)=(?P<value>[^\[\]]*)\]\Z")


def after_member_limbs(member):
    """The alternates of ONE member: `a|b` -> `['a', 'b']`, `a[g=y]` -> `['a[g=y]']`.

    ⚠ THE ORDER IS LOAD-BEARING and is `_manifest_after_ids`' own: bracketed content is
    NEUTRALISED BEFORE the alternate split, so a `|` INSIDE a guard value never reads as an
    alternate. Cutting the other way round is the strip-then-split defect (#3386): `a[g=y]|b`
    truncated at the first `[` and limb `b` vanished from the graph — an edge never traversed,
    reported clean. Blanked POSITIONALLY rather than removed, so each limb is sliced out of the
    ORIGINAL text and keeps its own guard for the member-grammar read.

    ⚠ THIS IS NOW THE ONLY BRACKET-NEUTRALISE IN THIS MODULE, and `parse_after_member` reaches
    the alternate test THROUGH it (task `one-readiness-predicate` D6). Before D6 the test was a
    `"|" in re.sub(...)` inlined in that function and there was nothing to split with, because
    nothing was allowed to evaluate an alternate. D6 made an alternate EVALUABLE, which needs the
    limbs — and one predicate answering "is this an alternate" while a second produced the limbs
    is the two-readings drift W1 collapsed one layer up. The verdict is unchanged in every case:
    `limbs != [t]` is true on exactly the tokens `"|" in re.sub(r"\\[[^\\]]*\\]", "", t)` was true
    on, INCLUDING the degenerate `"|"` and the malformed unclosed `a[k=v|x`.

    ⚠ A SECOND COPY LIVES IN `capabilities/goals-tree/tool/goal_cli.py#after_member_limbs`, which
    already imports `parse_after_member` from this file through its grammar bridge. Re-pointing it
    at this one is a real follow-up and is NOT done here (that file is outside this change); the
    two are byte-identical in algorithm and are named the same so a reader finds both.
    """
    blanked = re.sub(r"\[[^\]]*\]", lambda m: "\0" * len(m.group(0)), member)
    limbs, start = [], 0
    for i, ch in enumerate(blanked):
        if ch == "|":
            limbs.append(member[start:i])
            start = i + 1
    limbs.append(member[start:])
    return limbs


def parse_after_member(token):
    """(name, key, value, alternate) for ONE member of an `after` cell.

    `name`        the CLEAN seat name — what `terminal_disposition` is asked about.
    `key`/`value` the guard's two halves, or `(None, None)` on a bare member.
    `alternate`   True for an OR-alternate, which has MORE THAN ONE name and therefore no single
                  decomposition to return. The fourth slot's historical name is `unsupported`,
                  and it is kept on `AfterMember` and in every caller's unpacking because four
                  files outside this one read it positionally — what changed with D6 is not this
                  function's answer but what a CONSUMER may do with it.

    ⚠ THIS FUNCTION STILL REFUSES TO DECOMPOSE AN ALTERNATE, and that is not the same statement as
    "an alternate cannot be evaluated". `a[g=y]|b` asks "either of these": it resolves no single
    name, no single key and no single value, so returning one would be picking a limb here, in a
    parser, where nothing knows which limb ran. The EVALUATION is `after_member_state`'s — it
    splits with `after_member_limbs` and asks the same arithmetic of each limb (D6). Before D6
    there was no such evaluator and every consumer rendered `<unsupported-alternate>` and blocked."""
    t = (token or "").strip()
    # `_manifest_after_ids`' own ordering, reproduced — now inside `after_member_limbs`, which is
    # its one home. An alternate is a token the bracket-aware split does NOT hand back whole.
    if after_member_limbs(t) != [t]:
        return None, None, None, True
    m = GUARDED_MEMBER_RE.match(t)
    if m:
        return (m.group("name").strip(), m.group("key").strip(),
                m.group("value").strip(), False)
    return t, None, None, False


# ---------- 7.424 (W1): the COLLAPSE — one decomposition site, reached by every member ----------
#
# THE DIVERGENCE THIS CLOSES, verified at source before the fix (design D-6, this pass's §1 row 28).
# `taskforce_after` returned the `after` cell's members RAW and `parse_after_member` — added later,
# beside it — decomposed the same grammar. Two readings of one surface, and which one a consumer got
# depended on which function it happened to call: `edge-runner-job.py` (4 sites), `run-state-job.py`
# and `watch.py` all call `taskforce_after` and so all read `a[safe=yes]` as a SEAT NAME. Building a
# guard evaluator on top of that (W2) would have inherited whichever parser it reached.
#
# ⚠ THE COLLAPSE IS DIRECTIONAL: the PRODUCER routes through the READER, never the other way. There
# is exactly one decomposition of the member grammar in this module — `parse_after_member`, above,
# holding the only match of the guarded-member regex and the only bracket-strip-then-alternate — and
# `taskforce_after` is now its only production caller. A consumer cannot obtain a member that
# skipped it, which is what makes this a collapse rather than a third reading.
#
# ⚠ WHY A `str` SUBCLASS AND NOT A TUPLE OR A DATACLASS. Six consumer sites across three files are
# outside this change's grant and MUST keep comparing, hashing, joining and printing the member as
# the string it always was — a return-type change would have to land in all four files at once or
# break the room. This carries the decomposition WITHOUT changing what the token IS.
#
# ⚠⚠ AND THE PRICE OF THAT, STATED WHERE IT IS PAID: the attributes ride on the OBJECT, not on the
# text. Any ordinary string operation — a slice, `"".join(...)`, `str(x)`, a json round-trip, a
# re-read from disk — yields a PLAIN `str` that has silently lost them. Nothing raises at the loss
# site. That is why `after_member_parts` below REFUSES a plain `str` instead of falling back: a
# fallback reading "no attributes, therefore no key" would render a guarded member exactly like a
# bare one, which is this task's own defect rebuilt one layer down.


class AfterMember(str):
    """ONE member of an `after` cell: the raw token, carrying `parse_after_member`'s reading.

    It IS the string (`AfterMember("a") == "a"`, same hash, same repr through `str()`), so no
    consumer of `taskforce_after` sees a changed value. `name`/`key`/`value`/`unsupported` are
    exactly `parse_after_member`'s four, computed ONCE at construction — the single site."""

    def __new__(cls, token):
        member = super().__new__(cls, token)
        (member.name, member.key,
         member.value, member.unsupported) = parse_after_member(token)
        return member


def after_member_parts(member):
    """`(name, key, value, unsupported)` for one member — the ONE way a consumer reads it.

    REFUSES a plain `str` LOUDLY. A member that reaches a consumer without its decomposition has
    lost it somewhere between `taskforce_after` and here (a slice, a `join`, a json round-trip),
    and the failure is invisible at the loss site — so it is made visible at the READ site, which
    is the only place left that can see it. Never a fallback: `getattr(m, "key", None)` would read
    a lost decomposition as "this member has no guard", and a guarded member would render exactly
    like a bare one."""
    if not isinstance(member, AfterMember):
        raise TypeError(
            f"after member {member!r} is a plain {type(member).__name__}, not an AfterMember — "
            f"its decomposition was lost after `taskforce_after` produced it (a slice, a join, a "
            f"json round-trip and a re-read from disk all do this). Read members straight off "
            f"`taskforce_after`, or re-make one with `AfterMember(token)`. This refuses rather "
            f"than defaulting, because defaulting renders a guarded member as a bare one.")
    return member.name, member.key, member.value, member.unsupported


# The guard-value surface. NEW with this change, and deliberately its own file rather than a column
# on `taskforce.csv`: that file has ONE writer (the materialize command) and a ruling is not a
# materialization. Append-only, LAST ROW PER `(seat, key)` WINS — a supersession is an append, so
# the record of what was ruled first survives the ruling that replaced it.
#
# ⚠ AN ABSENT FILE MEANS "NO RULINGS YET", NEVER AN ERROR. Every package predating this change has
# no such file, and the fail-safe direction is that all their guarded edges stay BLOCKED — which is
# where they already were. The other direction (absent file ⇒ nothing to check ⇒ met) would admit
# every guarded row in every run in one release.
GUARD_VALUES_FILE = "guard-values.csv"
GUARD_VALUES_COLS = ["seat", "key", "value", "source", "ruled-by", "stamp"]


def load_guard_values(base):
    """{(seat, key): {col: cell}} from `coordination/guard-values.csv`. `{}` when absent."""
    header, rows = read_csv_table(Path(base) / GUARD_VALUES_FILE, [])
    if not rows or not {"seat", "key", "value"} <= set(header):
        return {}
    idx = {c: i for i, c in enumerate(header)}
    out = {}
    for r in rows:
        pad_row(r, header)
        seat, key = r[idx["seat"]].strip(), r[idx["key"]].strip()
        if seat and key:
            out[(seat, key)] = {c: (r[idx[c]].strip() if c in idx else "")
                                for c in GUARD_VALUES_COLS}
    return out


def guarded_pairs(pkg):
    """{(seat, key): [raw member tokens]} — every guarded pair a LIVE `after` member references.

    The verb's referenced-pair refusal reads this and nothing else: a ruling on a pair no edge
    consumes is a typo until proven otherwise, and a typo that writes is folklore."""
    out = {}
    for preds in taskforce_after(pkg).values():
        for p in preds:
            # 7.424: the decomposition is READ off the member, not re-derived. It was computed at
            # the one site when `taskforce_after` produced the member; a second
            # `parse_after_member(p)` here would be a second CALL of the one site — harmless — but
            # reading it off the object is what keeps the site single by construction.
            name, key, _value, unsupported = after_member_parts(p)
            if unsupported or key is None:
                continue
            out.setdefault((name, key), []).append(p)
    return out


def append_guard_value(base, seat, key, value, source, ruled_by):
    """APPEND one ruling row. Returns the row as written. Creates the file with its header."""
    path = Path(base) / GUARD_VALUES_FILE
    header, rows = read_csv_table(path, GUARD_VALUES_COLS)
    header, widened = widen_header(header, GUARD_VALUES_COLS)
    if widened:
        rows = [pad_row(r, header) for r in rows]
    idx = {c: i for i, c in enumerate(header)}
    row = ["" for _ in header]
    for col, val in (("seat", seat), ("key", key), ("value", value),
                     ("source", source), ("ruled-by", ruled_by), ("stamp", now())):
        row[idx[col]] = val
    rows.append(row)
    write_csv_table(path, header, rows)
    return {c: row[idx[c]] for c in header}


# ---------- U2.1 (7.224): the seat → STORE ROW binding ----------
#
# THE DEFECT THIS CLOSES. Until this term existed the seat-radius predicate read NO store input at
# all: `terminal(self)`, the roster, the descriptor and the predecessors' dispositions — every one
# of them a statement about a SESSION or a SEAT, none about the ROW the seat exists to discharge.
# So a seat whose row the run had already ruled concluded was offered for launch anyway, and on
# run-3 three of them sat in the live READY set at once (`both-goal-kinds-driver`,
# `c1-rehearsal-driver`, `staffer-launch-attributor` — all three `unreachable-by-construction`).
# Telling the caller the truth was already tried; it was ignored, which is why this refuses instead.
#
# THE AUTHORITATIVE SURFACE IS RULED, NOT CHOSEN HERE: the store ROW — its title line's `#`-tag
# tokens — per U1(b)'s `pick` = `row`
# (`runs/run-3/decisions.md#p-U1-terminal-state-design-ACCEPTED-PROVISIONAL-both-contradictions-settled-in-this-ruling`).
# The FIELD read is the row's `tags[]`, in the `row-outcome/` namespace.
#
# THE JOIN KEY IS RULED TOO, and against the shape this file could have reached more easily: the
# leader ruled it is `taskforce.csv`'s REFERENCE COLUMN and explicitly NOT a descriptor frontmatter
# key, on measured evidence that a `seat.md` is a one-shot projection already observed disagreeing
# with reality (a seat declaring `window: wave-rtss-1` while its pane sat in `wave-rtss-10`).
# `taskforce.csv` has ONE writer, the materialize command. NEVER KEY A JOIN ON THE SURFACE KNOWN TO
# DRIFT — so this reads the column and never the descriptor, even though the descriptor is nearer.
ROW_OUTCOME_TAG_PREFIX = "row-outcome/"

# The FIVE values that suppress an offer, spelled exactly as U1(a) enumerates them. BOTH classes,
# and that is the whole point of stating it as a set rather than as "the terminal ones": under the
# terminal-class-only reading the design fixes ONE of the seven measured mis-offers. A terminal's
# suppression never lifts; a holding state's lifts when its named exit event fires. They differ in
# WHEN, not in WHETHER.
#   terminal: no event exits them — offering is always wrong
#   holding:  an exit event exists and has NOT fired — offering is wrong until it does
# `done` and `untouched` are deliberately ABSENT: they are U1(a)'s `baseline` pair, carried by the
# checkbox and by the offerable state itself, and suppressing `untouched` would refuse every
# ordinary seat. An unenumerated `row-outcome/*` value does NOT suppress — it is RENDERED instead
# (see `--explain`), because over-refusal is as much a defect here as under-refusal and a value
# this file does not know is not a value it may act on.
ROW_OUTCOME_STOP_STATES = ("skipped-by-guard", "finished-unsatisfiable",
                           "unreachable-by-construction",      # terminal
                           "accepted-not-closable-yet", "held-by-ruling")  # holding

# The join column on `taskforce.csv`. ABSENT ON EVERY PACKAGE THAT HAS NOT ADDED IT, and its
# absence is NOT an error: the term simply binds nothing and every seat keeps the verdict it had.
# That is the fail-safe direction — a run with no join must not have all 149 of its seats refused.
TASKFORCE_STORE_JOIN_COLUMN = "store-id"

# The row's title line: `- [ ] 7.224 Title #tag #tag`. The tag grammar is `sb_task.py`'s TAG_RE,
# copied deliberately rather than imported — team-kit ships without the vault's task CLI on
# sys.path, and a silent ImportError here would make every row read as untagged, which is exactly
# the failure this term exists to end.
STORE_ROW_LINE_RE = r"^- \[[ x]\] {rid}(?:\s|$)"
STORE_TAG_RE = re.compile(r"(?:(?<=\s)|^)#([A-Za-z0-9_/-]+)")


def taskforce_store_ids(pkg):
    """{seat: raw `store-id` cell} from `taskforce.csv`. `{}` when the column does not exist.

    One producer, one parse — the same discipline `taskforce_after` states for the `after` cell."""
    header, rows = read_csv_table(pkg / "taskforce.csv", [])
    if not rows or "seat" not in header or TASKFORCE_STORE_JOIN_COLUMN not in header:
        return {}
    idx = {c: i for i, c in enumerate(header)}
    out = {}
    for r in rows:
        pad_row(r, header)
        seat = r[idx["seat"]].strip()
        if seat:
            out[seat] = r[idx[TASKFORCE_STORE_JOIN_COLUMN]].strip()
    return out


def resolve_store_path(pkg, rel):
    """The store file `rel` names, resolved from the package UPWARD, or None.

    NO WORKSPACE ROOT IS HARDCODED, by the same ruling that keeps window names out of this file: a
    path frozen into a tool every run shares refuses every run organized differently. So a
    workspace-relative cell is resolved the only way that needs no constant — try the package, then
    each ancestor, first hit wins. An absolute cell is taken as given."""
    p = Path(rel)
    if p.is_absolute():
        return p if p.is_file() else None
    for d in [Path(pkg)] + list(Path(pkg).resolve().parents):
        cand = d / p
        if cand.is_file():
            return cand
    return None


def store_row_outcome(pkg, cell, cache=None):
    """(values, note) — the `row-outcome/*` values on the store row this cell names.

    `values` is [] both when the row carries no such tag AND when the cell resolves to nothing;
    `note` is what tells those two apart, and it is rendered on EVERY seat rather than only on the
    ones that trip. AN UNRESOLVED JOIN NEVER SUPPRESSES: a cell this function cannot read is a
    missing measurement, and refusing on a missing measurement would turn a typo into a room-wide
    launch freeze. It is made LOUD instead — silence is what would make it dangerous.

    The cell is `<store-path>#<row-id>`; the path half may be omitted only if there is nothing to
    resolve, in which case the join is reported unresolved rather than guessed at."""
    cell = (cell or "").strip()
    if not cell:
        return [], "no `store-id` cell — this seat is bound to no store row"
    if "#" not in cell:
        return [], (f"UNRESOLVED JOIN: `{cell}` carries no store path. The cell is "
                    f"`<store-path>#<row-id>`; a bare row id names no file to read")
    rel, _, rid = cell.rpartition("#")
    if not rel or not rid:
        return [], f"UNRESOLVED JOIN: `{cell}` is not `<store-path>#<row-id>`"
    path = resolve_store_path(pkg, rel)
    if path is None:
        return [], f"UNRESOLVED JOIN: no file `{rel}` at or above {pkg}"
    if cache is None:
        cache = {}
    key = str(path)
    if key not in cache:
        try:
            cache[key] = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            cache[key] = []
            return [], f"UNRESOLVED JOIN: {path} could not be read ({e})"
    pat = re.compile(STORE_ROW_LINE_RE.format(rid=re.escape(rid)))
    line = next((ln for ln in cache[key] if pat.match(ln)), None)
    if line is None:
        return [], f"UNRESOLVED JOIN: no row `{rid}` in {path}"
    vals = [t[len(ROW_OUTCOME_TAG_PREFIX):] for t in STORE_TAG_RE.findall(line)
            if t.startswith(ROW_OUTCOME_TAG_PREFIX)]
    return vals, f"row `{rid}` in {path}"


def seat_store_outcomes(pkg):
    """{seat: {store-row, values, stop, note}} for every seat, join column present or not.

    PRESENT ON EVERY SEAT, never only on the ones it trips — 7.237's rule, and it is the same
    reason: `--explain` must render the value that DECIDED a term even when that value is the clean
    one, and a key that appears only when it fires cannot be read as a term of the predicate."""
    cells = taskforce_store_ids(pkg)
    cache = {}
    out = {}
    for seat, cell in cells.items():
        vals, note = store_row_outcome(pkg, cell, cache)
        out[seat] = {"store-row": cell, "values": vals, "note": note,
                     "stop": [v for v in vals if v in ROW_OUTCOME_STOP_STATES]}
    return out


def terminal_disposition(pkg, base, seat):
    """(ending, source, skew) from the ending store. Absence is not a stored word.

    ⚠ `skew` IS ALWAYS `None` AND THE SHAPE IS KEPT ON PURPOSE — it is the third element every
    caller still unpacks. Disposition SKEW was two ending records disagreeing (`awaiting-close.json`
    vs `sessions.csv`); §4.1 deleted the second writer, so there is nothing left for one record to
    disagree with. The tuple keeps its arity so no caller has to learn a new one; what changed is
    that the skew branch is now unreachable, which is the point of removing a second writer."""
    try:
        row = ending_store.get_current_ending(pkg, seat)
    except ending_store.EndingStoreError:
        row = None
    if not row:
        return None, "", None
    return row.get("ending"), "ending-store", None


# ---------- D6 (`one-readiness-predicate`): the MEMBER arithmetic, one home, alternates included --
#
# THE RULING THIS BUILDS. `plan-check-mechanization` depends on
# `plan-interviewer[use-case=optimize]|plan-interviewer[use-case=port]|plan-interviewer[use-case=scaffold]`,
# and every evaluator refused an alternate outright, so that seat was unreachable no matter what
# else was fixed. Owner-ruled 2026-08-11: AN ALTERNATE IS SATISFIED WHEN ANY ONE MEMBER IS
# SATISFIED. That is the reading the syntax already implies and the only one under which the live
# goal's DAG terminates.
#
# ⚠ WHY THE BRANCH SET MOVED OUT OF `ready_seat_rows`'S LOOP. A limb needs EXACTLY the arithmetic a
# top-level member gets — the same two terms in the same order, the same four renderings, the same
# structured entry — and the alternative to lifting it was a second copy inside the alternate arm.
# A second copy of a readiness term is the defect class 7.383 and 7.424 each closed once already.
#
# ⚠ AND `<unsupported-alternate>` IS GONE, not deprecated. It was the honest answer while no
# arithmetic existed; keeping it as a fallback branch would leave a path that BLOCKS a member the
# ruling says is satisfiable, and nothing on disk would say which path a given run took.

def after_member_state(member, term, guards):
    """(state, entry, met) for ONE `after` member — the WHOLE member arithmetic.

    `state` the rendered value, spent by the BLOCKED/READY reason string and by `--explain` alike.
    `entry` the structured UNMET member, or `None` when the member is MET.
    `met`   the CLEAN predecessor names that SATISFIED it — `[]` when it is unmet. A LIST, because
            an alternate can be carried by more than one limb, and every limb that ran left
            artifacts its successor is entitled to read (that is the `seed` field, D4). For a bare
            or guarded member it is `[]` or the member's one clean name.

    `term` is `{clean name: (value, source, skew)}` and `guards` is `load_guard_values`' map —
    passed IN rather than read here, because the caller hoists both ONCE per command and N members
    must not cost N reads of two files.
    """
    pname, gkey, gval, alternate = after_member_parts(member)
    if alternate:
        # D6: EITHER OF THESE. Each limb is re-made through `AfterMember` so it carries the same
        # decomposition a top-level member does — `after_member_parts` REFUSES a plain `str`, and
        # a limb sliced out of a token is exactly the "lost its decomposition" shape it refuses.
        limbs = [AfterMember(x.strip()) for x in after_member_limbs(str(member)) if x.strip()]
        sub = [(limb, after_member_state(limb, term, guards)) for limb in limbs]
        met = [n for _limb, (_s, _e, names) in sub for n in names]
        if met:
            # THE RENDERING NAMES THE LIMB THAT CARRIED IT, never a bare `done`. "This alternate is
            # satisfied" is not readable evidence; "satisfied BY THIS limb, on THIS value" is, and
            # it is the difference between a reader who can check the admission and one who cannot.
            return ("any-of -> " + " + ".join(f"{limb}={s}"
                                              for limb, (s, _e, names) in sub if names),
                    None, met)
        # UNMET: EVERY limb's own state, because "the alternate is unmet" sends the reader to look
        # up three predecessors by hand. The structured entry carries the raw token as its `seat` —
        # an alternate resolves no single roster row, which is stated rather than papered over with
        # a name that resolves to nothing — and each limb's own entry underneath it.
        return ("<any-of unmet: " + " ".join(f"{limb}={s}" for limb, (s, _e, _n) in sub) + ">",
                {"seat": str(member), "state": "alternate-unmet",
                 "limbs": [e for _limb, (_s, e, _n) in sub]},
                [])
    pv, _psrc, pskew = term.get(pname, (None, "", None))
    if pskew:
        return f"SKEW({pskew[0]}|{pskew[1]})", {"seat": pname, "state": "skew",
                                                "skew": [pskew[0], pskew[1]]}, []
    if pv is None:
        return "<no check-out>", {"seat": pname, "state": "no-check-out"}, []
    if pv != "done":
        return pv, {"seat": pname, "state": pv}, []
    if gkey is None:
        # A BARE member, met — rendered exactly as it was before 7.383 existed.
        return "done", None, [pname]
    # 7.383: the SECOND term, reached only once the dependency half is `done`. The order is the
    # design — a guarded edge whose predecessor never finished must read as an unfinished
    # predecessor, not as an unruled guard, or the reason names the wrong thing to fix.
    ruling = guards.get((pname, gkey))
    if ruling is None:
        return (f"<guard {gkey} unruled>",
                {"seat": pname, "state": "guard-unruled",
                 "guard": {"key": gkey, "required": gval}}, [])
    if ruling["value"] != gval:
        return (f"<guard {gkey}={ruling['value']}>",
                {"seat": pname, "state": "guard-mismatch",
                 "guard": {"key": gkey, "required": gval, "ruled": ruling["value"]}}, [])
    # MET — and `done` alone would say the predecessor finished while saying NOTHING about the
    # ruling that actually admitted the edge. Two facts carried this member; the met rendering
    # names both.
    return "done+guard-ruled", None, [pname]


# ---------- D72: THE WALK-FORWARD — who already ran on a `done` a `--reopen` is about to retract --
#
# D54 lets the leader re-open a `done` row; D72 settles the question the two feasibility lanes left
# open ("should anything downstream be told?") in the FULLER direction: the SYSTEM flags every
# downstream seat that already ran depending on that `done`, automatically, at reopen time.
#
# ⚠ THIS IS A REVERSE LOOKUP ("who names me"), NOT A FORWARD READINESS EVALUATION. It reuses the
# SAME member grammar `after_member_state` reads — `taskforce_after`/`AfterMember`/
# `after_member_limbs` — per D72's own constraint ("compute it from the same predicate the plan
# already uses... a duplicate drifts"), but it does not call `after_member_state` itself: that
# function asks "is THIS member satisfied", which needs `term`/`guards` and a guard ruling; this
# asks only "does this member's after-cell NAME the reopened seat at all", which needs neither.

def _reopen_predecessor_names(member):
    """Every predecessor NAME one `after` member can resolve to — the bare name, or every limb's
    name for an alternate (`a|b` names BOTH `a` and `b`, since a reopen of EITHER retracts a
    `done` the alternate may have been satisfied by)."""
    if member.unsupported:
        return [AfterMember(limb).name for limb in after_member_limbs(str(member))
                if AfterMember(limb).name]
    return [member.name] if member.name else []


def reopen_downstream_seats(pkg, reopened_seat):
    """Every seat whose `after` NAMES `reopened_seat` as a predecessor AND that already has a
    session row (open or ended) in `sessions.csv` — work that RAN on the `done` a `--reopen` of
    `reopened_seat` is about to retract. `[]` when nothing downstream has run yet (the common
    case: reopen is admitted the moment a `done` row exists, long before any successor need have
    started).

    Does NOT roll anything back, re-block anything, or touch any other seat's row — D54/D72 grant
    a FLAG, never an undo. The caller (the `--reopen` admission block) is what prints and records
    this list; this function only computes it."""
    after = taskforce_after(pkg)
    path = sessions_csv(pkg)
    ran = set()
    if path.exists():
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if "seat" in idx:
            for r in rows:
                pad_row(r, header)
                s = r[idx["seat"]].strip()
                if s:
                    ran.add(s)
    hits = []
    for seat, members in after.items():
        if seat not in ran:
            continue
        for m in members:
            if reopened_seat in _reopen_predecessor_names(m):
                hits.append(seat)
                break
    return sorted(set(hits))


# ---------- D22: THE DERIVED `dead` STATE — a branch that CAN NEVER RUN is not pending ----------
#
# THE DEFECT THIS CLOSES, measured 2026-08-19 on both production goals. A goal's `taskforce.csv`
# registers ONE SEAT PER `planning-mode` VARIANT — `plan-task-definer` behind
# `plan-dag-structurer[planning-mode=full]` and `plan-planner` behind the `collapsed` twin — copied
# verbatim from the workflow manifest at materialization. The lane's structurer rules ONE value, so
# the other variant, and every seat downstream of it, is BLOCKED FOREVER BY CONSTRUCTION. Nothing
# said so: `engine/seeding.js`' frozen-at-seeding guard counted "not `done`" as pending and fired a
# goal-frozen alarm on a healthy goal (14 of stools' 16 non-done rows, 13 of meet's 31). An alarm
# that fires on healthy goals is an alarm the owner learns to ignore, which reinstates the failure
# mode the whole redesign exists to close. Root-cause record:
# `1-projects/build-ignite/build/root-cause-unblock-goals/dead-branch-mode-guards-2026-08-19.md`.
#
# ⚠ IT IS DERIVED AT READ TIME AND NEVER STORED (owner ruling D22, option a of three). No ledger
# write, no new file, no migration, nothing that can drift from the rows it describes.
#
# ⚠ THE FORK IS DISCHARGED BY `guard-values.csv` AND BY NOTHING ELSE — never by
# `planning/current/planning-mode.json`, which has zero consumers BY DESIGN (goal-side ruling
# `d-guard-values-is-the-fork-mechanism`). That is not a preference: the polarity is PER LANE, not
# per goal. On `meet-transcript-summarizer` the unprefixed lane runs `collapsed` while the `plan-3`
# lane runs `full`, so a fix reading ONE goal-level mode value gets one of the two lanes backwards.
# Resolving each guarded member against ITS OWN `(predecessor, key)` ruling row gives per-lane
# correctness for free, because each lane's structurer owns its own row.
#
# ⚠ AND IT READS THE ONE EVALUATOR'S ANSWER, NEVER A SECOND PARSE. The input is
# `after_member_state`'s structured `unmet-after` entry — the same computation the reason string
# and `--explain` spend. A reachability notion built on a fresh read of the `after` cell would be
# the second decomposition 7.424 collapsed, rebuilt one layer up (PRIN-11).
#
# WHAT IS DEAD, EXACTLY, and every clause is load-bearing:
#   guard mismatch   the predecessor is `done`, a ruling for `(predecessor, key)` EXISTS, and its
#                    value differs from the member's required one. A ruling for a FINISHED seat
#                    does not change, so the member can never be met.
#   NOT unruled      `<guard k unruled>` stays ordinary pending — the structurer has not run yet,
#                    and calling that dead would bury every guarded edge in every young goal.
#   NOT pending      a predecessor that has not reached `done` has ruled nothing to judge against.
#   alternates OR    `a|b` is dead only when EVERY limb is dead — one live limb keeps it alive.
#   conjuncts AND    a seat is dead when ANY ONE of its members is dead; the cell is a conjunction.
#   transitive       a member whose named predecessor is a DEAD SEAT is dead, iterated to a
#                    fixpoint — without it the 11 rows downstream of a dead variant keep the false
#                    positive alive on their own, rendering the indistinguishable `<no check-out>`.


def dead_after_entry(entry, dead):
    """True when this UNMET `after` member entry can NEVER become met. `dead` is the seat set.

    The entry is `after_member_state`'s own structured answer, not a re-reading of the `after`
    cell — see the block above. Every state it does not name (`no-check-out`, `skew`, a raw
    disposition, `guard-unruled`) is ALIVE unless the predecessor it names is itself dead, which
    is the fail-safe direction: an unrecognised state must never be counted dead, because a dead
    seat is a seat the freeze alarm stops watching."""
    if not entry:
        return False
    state = entry.get("state")
    if state == "guard-mismatch":
        return True
    if state == "alternate-unmet":
        limbs = entry.get("limbs") or []
        # `all([])` is True — an alternate with no limbs would read DEAD on an empty list, which is
        # the one input this predicate must never accept on faith.
        return bool(limbs) and all(dead_after_entry(e, dead) for e in limbs)
    return entry.get("seat") in dead


def dead_entry_why(entry):
    """WHY this member is dead, in the words the reason string prints."""
    if entry.get("state") == "guard-mismatch":
        g = entry.get("guard") or {}
        return (f"`{entry['seat']}[{g.get('key')}={g.get('required')}]` needs "
                f"`{g.get('key')}={g.get('required')}` and `{entry['seat']}` FINISHED having "
                f"ruled `{g.get('key')}={g.get('ruled')}`")
    if entry.get("state") == "alternate-unmet":
        return f"EVERY alternate of `{entry['seat']}` is itself dead"
    return f"its predecessor `{entry['seat']}` is itself dead"


def mark_dead_rows(rows):
    """Set `dead` on EVERY row (True/False, never absent) and name it in the dead rows' reason.

    Returns the dead seat names. Present on every row for the same rule and the same reason
    `unmet-after`, `row-outcome` and `undeclared-session` are: a key that appears only when it
    fires cannot be read as a term, and an ABSENT key raises in a consumer where a false decides.

    ⚠ IT IS A FIELD, NOT A VERDICT VALUE, and that is a measured choice rather than a taste. The
    launch-admission predicate's class map (`CLASS_TO_VERDICT`) is asserted row-by-row against this
    home's verdicts by the self-test's arm 1, and a dead row's admission class is
    `unmet-predecessor` — whose verdict IS `BLOCKED`. A new `DEAD` verdict word would therefore
    have to land in the admission predicate too, which reads FIELDS and deliberately never reads
    `verdict` (`no-class-clause`). A dead seat IS blocked; `dead` says the block is permanent. Every
    existing consumer — `seeding.js`' `verdict === 'READY'` door, its `HELD` and `SKEW` filters —
    is untouched by construction, and a consumer that has never heard of `dead` keeps the answer
    it has today.

    ⚠ ONLY A `BLOCKED` ROW IS A CANDIDATE. Every verdict above `BLOCKED` in the ladder is a fact
    about the seat ITSELF (a check-out, a skew, an owner ask, an occupied roster row), and none of
    them is made permanent by an unsatisfiable predecessor.

    The fixpoint is a re-sweep per newly-dead seat — O(seats × dead) on a graph of tens of rows,
    against `unmet-after` lists already in memory. Nothing here re-reads a file."""
    dead = set()
    changed = True
    while changed:
        changed = False
        for r in rows:
            if r["seat"] in dead or r["verdict"] != "BLOCKED":
                continue
            if any(dead_after_entry(e, dead) for e in r["unmet-after"]):
                dead.add(r["seat"])
                changed = True
    for r in rows:
        r["dead"] = r["seat"] in dead
        if not r["dead"]:
            continue
        _why = next((dead_entry_why(e) for e in r["unmet-after"]
                     if dead_after_entry(e, dead)), "an unsatisfiable `after` member")
        r["reason"] += (
            f"   ⚠ DEAD, NOT PENDING — this seat can NEVER run: {_why}. It is a mode-variant "
            f"branch the lane did not take (or something downstream of one), so it is not owed "
            f"work and NOTHING is waiting on it. Do not count it as pending, do not retry it, do "
            f"not alarm on it. DERIVED at read time from `guard-values.csv`, never stored")
    return dead


def ready_seat_rows(args):
    """[{seat, verdict, reason, ...}] for every `taskforce.csv` row, in file order.

    ONE ROW PER SEAT, AND EVERY ROW CARRIES A REASON. A bare verdict re-installs agent judgment
    at the read: the caller would have to reconstruct WHY, and reconstruction is exactly the act
    the chief-of-staff's engine bounds forbid it.

    Verdict precedence, and the order is the design:
      SKEW     first, always — a contradiction must never be masked by a later verdict
      HELD     (W2) this seat has at least one POSTED, still-open `open_asks` row addressed to
               the OWNER — spec-state-store §2.1, the ONE source (it was the bus until the
               state-store migration, which is the dual-source defect that swap closes). Its
               dependents WAIT. ⚠ IT SITS ABOVE `DONE` DELIBERATELY, and that placement IS the mechanism:
               the whole purpose of the hold is that a seat which checked out WHILE its question
               to the owner was unanswered must not advance its successors, so a terminal
               disposition — the very thing such a seat carries — must never mask it. Below `SKEW`
               for the reason `SKEW` is first at all: two records disagreeing about this seat's
               own ending is a contradiction, and nothing, hold included, is decided over it.
               ⚠ UNIVERSAL, and every narrowing it could carry is DELIBERATELY ABSENT (owner
               ruling, safe-hold default): NOT gated on `fallback: block-and-queue`, NOT on
               whether the ferry delivered the ask, NOT on the seat's declared interactivity.
               Those three gates were the root cause of the incident this program closes — each
               one is a way for a real unanswered question to release the DAG anyway.
               ⚠ IT IS NOT `BLOCKED`. `BLOCKED` means an `after` member is unsatisfied — a fact
               about this seat's PREDECESSORS. `HELD` is a fact about this seat's own OPEN
               QUESTION. Merging them loses which of the two a human must act on.
      DONE     this seat already has a terminal disposition on record (`terminal(S) is not None`),
               so it is not a candidate to launch. ⚠ THE WORD IS THE COARSE CLASS, NOT A CLAIM
               THAT THE WORK IS DONE: the reason string and the json `disposition` field always
               name the actual value, and for `exited` the reason carries the routing in full.
               Nothing here maps `exited` to `done`.
      RENEWING / RENEW-BLOCKED  (THE RENEW GATE, 2026-08-18) the two halves `renew` splits into,
               AT `DONE`'S RUNG AND NOWHERE ELSE — this pair moved nothing above it, so `SKEW`
               and `HELD` still decide first and a contradiction about this seat's ending is
               still masked by neither. `renew` used to read `DONE` beside `exited`, which made
               "I am coming back" and "my harness died" one word. `RENEWING` is IN PROGRESS and
               is NOT the failure class; `RENEW-BLOCKED` is a halt with the marker's own reason
               in the string. ⚠ NEITHER ADVANCES AN EDGE — `after_member_state` reads the raw
               `renew` VALUE, which is not `done` — so the split is the REPORT axis only. The
               source is `renewal_state`, the ONE reader of the successor signal.
      RUNNING  an ACTIVE roster row — the seat is occupied; launching it again double-launches it
      UNBUILT  name in neither register (taskforce.csv ∪ sessions.csv) — not a missing folder
      UNDECLARED  (7.237) this seat's LAST ENDED session declared NO disposition — its work
               CONCLUDED and nobody asserted how it ended. NOT a launch candidate, and NOT a
               relaunch: relaunching re-runs finished work, which is the harm. Routes to the
               `leader` as a defect. ⚠ IT SITS ABOVE `BLOCKED` DELIBERATELY — a member of this
               class whose own `after` set happens to be unmet would otherwise read as an
               ordinary BLOCKED and its undeclared ending would never surface. Measured: of the
               three members on run-3, one (`briefing-collision-verifier`) was masked exactly
               that way while the other two sat in the live READY set.
      STOPPED  (7.224) the seat's BOUND STORE ROW carries a `row-outcome/*` STOP-STATE — the run
               has already ruled that row concluded or held, so offering the seat offers work the
               run has settled. THE ROW GOVERNS AND THE SEAT SURFACE DOES NOT: the row-outcome
               claim's subject is the ROW, and a surface whose subject is the SESSION cannot carry
               a claim about a row without re-collapsing the two. ⚠ IT SITS ABOVE `BLOCKED` for
               exactly 7.237's reason — a stop-state row whose `after` set happens to be unmet
               would otherwise read as an ordinary BLOCKED and its stop-state would never surface.
               ⚠ AND BELOW `UNDECLARED` DELIBERATELY: both verdicts refuse the offer identically,
               so precedence decides only WHICH reason prints, and `UNDECLARED` names an
               unresolved DEFECT the leader must act on, which would be lost if a settled state
               printed over it. Ordering them the other way changes no seat's offerability.
      BLOCKED  at least one `after` member is unsatisfied. A member is satisfied when its named
               predecessor checked out `done` — plus, for a GUARDED member, a recorded value
               matching its guard (7.383); an ALTERNATE (`a|b`) is satisfied when ANY ONE of its
               members is (D6). `after_member_state` is that whole arithmetic, in one place.
      READY    every term above cleared

    ⚠ EVERY ROW ALSO CARRIES `seed` (D4) — the resolved absolute paths of the declared outputs of
    the predecessors that satisfied its members, `[]` on a root. On a READY row that is the
    complete input set a launcher hands the seat; on any other row it is partial by construction
    and is not a launch input. See the field's own note below.

    ⚠ `UNDECLARED` REMOVES SEATS FROM `READY` AND ADDS NONE. A consumer that filters
    `verdict == "READY"` — which is what the launch-offer path does — cannot be handed one of
    these seats even if it never reads the reason string, and a consumer that does not know the
    value simply fails to match it. Both directions are fail-safe; neither advances an edge.
    """
    pkg = package_dir(args, register=False)
    base = base_dir(args, register=False)
    after = taskforce_after(pkg)
    _, _, roster = load_workers(base)
    # `register=False`, for the same reason `package_dir`/`base_dir` above carry it: this command's
    # docstring says it writes nothing, and `workers_dir`'s default resolution (re-)registers the
    # run tag — a WRITE, in `~/.config/rbtv/coordinate-runs.json`. Resolved ONCE into a local: the
    # UNBUILT reason below spends the same value, and re-resolving it there was a second door onto
    # the same registration.
    wdir = workers_dir(args, register=False)
    # D4: THE DESCRIPTORS ARE KEPT, not reduced to a name set on the spot. The seed below resolves
    # a predecessor's declared `outputs:` against that seat's own absolutized `cwd`, and both live
    # on this dict — so keeping it costs NOTHING (the same single `discover_workers` call this
    # line always made) while re-reading it per predecessor would cost one descriptor sweep per
    # edge. `built` is derived from it and is the identical set it always was.
    seat_desc = {w["agent"]: w for w in discover_workers(wdir)}
    built = registered_seats(pkg)
    # ⚠ THE `awaiting-close.json` HOIST IS GONE WITH ITS FILE [spec-state-store §4.1 Row A]. It
    # read a debt map and threaded it into `terminal_disposition`, which has answered off the ONE
    # ending store since that migration and ignored the argument. A hoist of a stub that answers
    # `{}` is not a cheap read, it is a read of nothing.
    # 7.237: hoisted ONCE — N seats must cost one read of
    # `sessions.csv`, not N. The map feeds `undeclared_endings` directly so the undeclared term and
    # `session_disposition` are answering about THE SAME selected row rather than two reads that
    # could straddle a concurrent append.
    # D42: the hoist now reads the WHOLE row and PROJECTS the pair, so the hold cell and the
    # disposition cell come from THE SAME selected row and the file is still read exactly once.
    last_ended_rows = sessions_last_ended_rows(pkg)
    last_ended = last_ended_pairs(last_ended_rows)
    # ⚠ THE UNDECLARED TERM IS COMPUTED AFTER THE `term` MAP, NOT HERE, and the move is a cost
    # fix rather than a reordering preference: it needs each seat's ENDING, `term` already reads
    # exactly that, and the store's client is a subprocess. Its first USE is far below, so nothing
    # between here and there sees a different value. `last_ended` stays hoisted at this line.
    # 7.224: hoisted ONCE for the same reason `awaiting` and `undeclared` are — N seats must cost
    # one read of the store file, not N. `seat_store_outcomes` caches per resolved path internally.
    outcomes = seat_store_outcomes(pkg)
    # THE RENEW GATE'S SIGNAL, hoisted ONCE for the same reason every hoist above is — N seats must
    # cost one read of `lifecycle-inflight.json`, not N. It is spent through `renewal_state`, which
    # is the ONE reader of it (see that function's own note); nothing here re-derives its arms.
    lifecycle = load_lifecycle(base)
    # W2: THE OWNER-ASK HOLD'S ONE READ OF THE ENDING STORE (spec-state-store §2.1), hoisted for
    # the same reason as every hoist above — N seats must cost ONE read, not N.
    #
    # ⚠ THE SOURCE IS `open_asks` AND NO LONGER THE BUS, and that swap IS the fix. This row used
    # to key `HELD` on `coord.open_asks(messages.md, to=owner)` while `engine/ending-reads.js#
    # recordView` keyed the SAME fact on the `open_asks` table — one fact, two sources, which is
    # the dual-source shape §2.1 exists to end. The two disagreed the moment either surface moved:
    # a posted ask that never reached this room's `messages.md` held the engine and not this
    # verdict, and a bus ask nobody posted held this verdict and not the engine.
    # `list_open_asks` is `seat_waiting_on_owner`'s own WHERE clause returned as rows, so
    # `waiting_on_owner` below and `held-asks` here can never disagree about one seat.
    #
    # ⚠ THE RELEASE MECHANISM MOVED WITH IT. A hold lifts when the ask is REAPED (§2.8:
    # `reapAndRelaunch` flips the row to `closed` in the same transaction that signals the seat's
    # relaunch), not when a `send --type answer --re <n>` row lands on the bus. Nothing here pairs,
    # counts or settles a second time.
    #
    # ⚠⚠ IT DEGRADES, IT NEVER RAISES, AND THE BROAD `except` IS THE DESIGN. The ignite engine's
    # seeding pass is FAIL-CLOSED PER GOAL: a non-zero exit from this command seeds NOTHING for the
    # whole goal. So an unreachable, locked or absent store must cost the run its HOLDS — never its
    # other verdicts. Missing db, node failure, malformed payload, anything: no holds, `[]` on
    # every row, exit 0, every other term intact.
    held = {}
    try:
        for _ask in ending_store.list_open_asks(pkg):
            held.setdefault(_ask["seat"], []).append(_ask["ask_id"])
    except Exception:                                          # noqa: BLE001 — see the note above
        held = {}
    # ── W3 · THE ON-DEMAND TERM — how many messages a STAFF CHAIR has waiting ──────────────────
    #
    # A staff chair is a real `taskforce.csv` row with NO `after` set, so on its own account it
    # reads READY the instant a goal materializes — and the daemon's seeding pass, which is a
    # `verdict == "READY"` filter and nothing else, would spawn the leader of every goal at goal
    # start with an empty inbox. The chair is spawned ON UNREAD MAIL and at no other time, so mail
    # is a TERM OF THE VERDICT, not a note beside one.
    #
    # ⚠ IT IS THE CHAIR'S UNREAD COUNT, NOT THE LOG'S TOTAL (W7, owner-ruled 2026-08-14). The W3
    # original raw-counted every row ever addressed to a staff chair and claimed in this very
    # comment to "count only the never-sat case" — it does not. A raw count has no cursor, so once
    # ANY message has been addressed to a chair the term is permanently non-zero, the IDLE branch
    # below stops firing forever, and the daemon's bare `verdict == "READY"` seeding pass re-spawns
    # the chair on every wake window. Falsified on `meet-transcript-summarizer`: the leader chair
    # had NEVER sat, the goal already carried 12 `to: leader` rows, and the freshly minted chair was
    # seeded READY 3 minutes after minting.
    #
    # The fix REUSES what this file already has rather than inventing a second cursor: the per-seat
    # `lastread` on the `workers.md` row, resolved by `unread_for()` ("P26 — persisted cursor"),
    # which is the SAME predicate `read` uses — so what the chair would see on an unfiltered `read`
    # and what this verdict counts can never disagree. A never-sat chair holds no roster row at all,
    # so its cursor reads 0 and every addressed row counts: the never-sat case is preserved exactly,
    # and the sat-then-drained case now correctly reads zero.
    #
    # ⚠ DEGRADES TO ZERO, NEVER RAISES — same rule and same reason as the hold above. An unreadable
    # bus must cost the run its WAKES, never its other verdicts, and zero is the fail-CLOSED
    # direction here: it leaves the chair IDLE rather than spawning one nobody asked for.
    staff_mail = {}
    _staff_after = [_s for _s in after if is_staff_seat(_s)]
    if _staff_after:
        try:
            _sm_blocks = load_messages(base)[1]
            _sm_rows = load_workers(base)[2]
            _sm_gmap = group_map(base)
            _sm_observers = observer_sets(args)[0]
            _sm_closing = closing_seats(base)
            for _s in _staff_after:
                _sm_row = current_row(_sm_rows, _s)
                _sm_start = (int(_sm_row["lastread"])
                             if _sm_row and _sm_row["lastread"].isdigit() else 0)
                staff_mail[_s] = len(unread_for(args, base, _s, _sm_start, _sm_blocks,
                                                _sm_gmap, _sm_observers, _sm_closing))
        except Exception:                                      # noqa: BLE001 — see the note above
            staff_mail = {}
    # 7.383: every member token parsed ONCE — and as of 7.424 that ONCE happens where the member is
    # PRODUCED (`taskforce_after` -> `AfterMember` -> `parse_after_member`), not in a map built
    # here. The member still carries the RAW token, which is what `preds` holds and what the reason
    # string must keep rendering, AND its decomposition, whose CLEAN name is what the LOOKUP uses.
    # Those are two different needs of one token; collapsing them is the defect 7.383 closed, and
    # having two places that decompose the token is the one 7.424 closes.
    members = [p for preds in after.values() for p in preds]
    # 7.383: hoisted ONCE, for the same reason `awaiting`, `undeclared` and `outcomes` are — N
    # guarded members must cost one read of the ruling file, not N.
    guards = load_guard_values(base)
    term = {}
    for seat in after:
        term[seat] = terminal_disposition(pkg, base, seat)
    # A predecessor named in an `after` set but carrying no row of its own is still a real term of
    # the predicate — resolved here so a dangling edge reads as "no check-out" rather than raising.
    # 7.383: resolved on the CLEAN name. An OR-alternate resolves NO name — it has more than one,
    # which is why it has no single decomposition.
    # D6: SO ITS LIMBS' NAMES ARE RESOLVED INSTEAD. Before D6 an alternate was SKIPPED here, which
    # was right while nothing downstream could evaluate one; `after_member_state` now asks `term`
    # about every limb, and a limb absent from this map would read `<no check-out>` for a reason
    # that has nothing to do with the limb's actual check-out.
    for _member in members:
        _limbs = ([_member] if not after_member_parts(_member)[3]
                  else [AfterMember(_x.strip()) for _x in after_member_limbs(str(_member))
                        if _x.strip()])
        for _limb in _limbs:
            _name = after_member_parts(_limb)[0]
            if _name and _name not in term:
                term[_name] = terminal_disposition(pkg, base, _name)

    # 7.237's undeclared term, computed HERE so it spends the endings `term` has already read
    # rather than asking the store a second time per seat (see the note where `last_ended` is
    # hoisted). A seat with an ended row and no `after` entry is absent from `term` and is read
    # by `undeclared_endings` itself — the injection is a saving, never a narrowing.
    undeclared = undeclared_endings(pkg, last_ended=last_ended,
                                    endings={_s: _v[0] for _s, _v in term.items()})

    out = []
    for seat, preds in after.items():
        value, source, skew = term[seat]
        row = current_row(roster, seat)
        active = bool(row) and row.get("active") == "yes"
        # 7.273: THE UNMET SET, HOISTED out of the terminal `else` below so that EVERY row reaches
        # it. The computation is unchanged and unmoved in substance — it is the SAME loop over the
        # SAME `term` reads the `else` has always run; only its position changed, because a row
        # taking any earlier branch never executed it and would carry no value at all.
        # TWO SHAPES, ONE PASS: `unmet` is the prose membership the BLOCKED `reason` string has
        # always rendered and is spent there UNCHANGED; `unmet_after` is the structured, LOSSLESS
        # form the launch-admission predicate reads as a term of the ROW. Lossless is the word
        # that matters: the skew pair rides as its two members rather than collapsing to the bare
        # word the prose renders inside `SKEW(a|b)`, so the field and the string it must agree
        # with carry the same membership, the same order, and the same information.
        unmet = []
        unmet_after = []
        # 7.383: THE PER-MEMBER RENDERING, COMPUTED ONCE HERE AND READ BY `--explain`. It used to
        # re-derive its own by looking each member up in the OUTPUT ROWS by name — which is the
        # SAME name-lookup this task exists to fix, in a second home: a guarded token matches no
        # output row, so `--explain` printed `<no check-out>` on its own account and would have
        # kept printing it even after the loop above was fixed. One computation, one home (PRIN-11).
        render = {}
        # D4 (`one-readiness-predicate`): THE SEED — the resolved absolute paths of the declared
        # outputs of the predecessors that SATISFIED this row's `after` members, de-duplicated with
        # ORDER PRESERVED (two predecessors may declare the same artifact). A ROOT SEAT GETS `[]`,
        # and that is a correct and complete seed, not a failure — the root case is the one an
        # implementation keyed on predecessors forgets.
        seed, seed_seen = [], set()
        for p in preds:
            # 7.383: THE PROSE KEEPS THE RAW TOKEN, THE STRUCTURE CARRIES THE CLEAN NAME. A reader
            # of the reason must see the guard that held the edge — dropping it renders a guard
            # failure as an ordinary unfinished predecessor. A CONSUMER resolves a roster by the
            # seat name, and `name[key=value]` matches no roster row anywhere.
            #
            # ONE CALL PRODUCES ALL THREE SHAPES. `state` is the rendered value (prose and
            # `--explain` alike); `entry` is the structured member, or `None` when the member is
            # MET; `met_names` is the clean predecessor name(s) that carried it. Deriving any of
            # them from another after the fact means splitting `raw=state` on `=`, and a guard's
            # own `=` sits inside the raw token — the split would cut in the wrong place on exactly
            # the members this arithmetic is about.
            #
            # `render[p]["met"]` is the call's OWN answer (an `entry` means unmet), never a re-test
            # of the rendered word against a literal — a `met` derived by matching `state` against
            # `("done", "done+guard-ruled")` would be a second copy of that branch set, and would
            # silently go wrong the day a met rendering gains a third form (D6 added two).
            state, entry, met_names = after_member_state(p, term, guards)
            render[p] = {"state": state, "met": entry is None}
            if entry is not None:
                unmet.append(f"{p}={state}")
                unmet_after.append(entry)
            # ⚠ THE SEED RESOLVES THE CLEAN PREDECESSOR NAME, NEVER THE RAW MEMBER TOKEN.
            # `seats/fx-route[risk=high]/` is a directory that cannot exist, and looking one up
            # yields a SILENTLY EMPTY seed — the same name-lookup defect 7.383 closed at the
            # readiness loop, one stage downstream. `met_names` carries the decomposition's clean
            # name(s) and nothing else; for a bare member that IS the token, so no plain row moves.
            for _name in met_names:
                _w = seat_desc.get(_name)
                # A predecessor with no descriptor contributes nothing (a dangling edge the leader
                # ruled `done`), and so does one carrying the RETIRED `outputs:` frontmatter key
                # (D3): its declaration surface is refused, and seeding a successor off a refused
                # descriptor is worse than seeding it with less. `declared_outputs` REFUSES that
                # descriptor at the seat's own
                # `done` check-out, so the only way one reaches here is a leader's ruling
                # over an `exited` row — which does not open the descriptor. Hence the check.
                if _w is None or _w["outputs_defect"]:
                    continue
                for _tok, _path in resolved_outputs(_w):
                    if _path not in seed_seen:
                        seed_seen.add(_path)
                        seed.append(_path)
        # ⚠ `disposition`/`source` ARE THE TERMINAL-DISPOSITION SIGNAL, AND THERE IS NO SECOND ONE.
        # W2 moved done-ness OUT of the execution record's `outcome` column (now the process
        # vocabulary `clean|crashed|killed`) and onto the seat's own check-out — which is this
        # pair, already emitted on EVERY row, with `terminal(S)` deriving the `DONE` verdict from
        # it. `engine/seeding.js#recordView` is the consumer. Stated here because the obvious W2
        # move is to add a field for what these two have always carried.
        _rn_state, _rn_why = (renewal_state(base, seat, lifecycle=lifecycle)
                              if value == "renew" else (None, ""))
        rec = {"seat": seat, "after": list(preds), "disposition": value, "source": source,
               # D42: present on EVERY row (`""` when unheld), same rule and same reason as
               # `undeclared-session` and `row-outcome` below — a key that appears only when it
               # fires cannot be rendered as a term, and `--explain` must show the clean value too.
               # ⚠ IT IS NOT A TERM OF THE VERDICT and must never become one: a held row keeps its
               # real class and keeps blocking its successors. The ONE consumer is the goal
               # watcher's owed scan.
               # W2: the open owner-ask IDS (§2.1 `open_asks.ask_id`, a Slack thread id — NOT
               # a bus message number), present on EVERY row (`[]` when none) — the same
               # rule and the same reason as `undeclared-session`, `row-outcome` and `unmet-after`:
               # a key that appears only when it fires cannot be read as a
               # term, and an ABSENT key raises in a consumer where an empty list decides.
               "held-asks": held.get(seat, []),
               "skew": list(skew) if skew else None, "active": active,
               "built": seat in built,
               # 7.237: present on EVERY row (None when the ending was declared), never only on
               # the rows that trip. A key that appears only when it fires cannot be rendered as
               # a term of the predicate, and `--explain` must show the value that DECIDED a
               # term even when that value is the clean one.
               "undeclared-session": undeclared.get(seat),
               # 7.224: present on EVERY row, join column or no join column — same rule, same
               # reason as `undeclared-session` above. `{}` would be a key that means "clean";
               # this carries the NOTE that says WHY it is clean, which is the difference between
               # "the row carries no stop-state" and "nothing was read at all".
               "row-outcome": outcomes.get(
                   seat, {"store-row": "", "values": [], "stop": [],
                          "note": "no `store-id` column on this run's taskforce.csv — the seat "
                                  "→ store-row join is not made on this package"}),
               # 7.273: present on EVERY row — `[]` when nothing is unmet, never only on the rows
               # that trip. Same rule and same reason as `undeclared-session` and `row-outcome`
               # above, applied to a third key: a consumer of the launch-admission predicate reads
               # this as a term of the ROW, and an ABSENT key raises where an empty list decides.
               # It is therefore a term of that boolean's safety, not a presentation choice.
               # ⚠ IT CARRIES NO VERDICT. The value is the same membership the BLOCKED `reason`
               # string names, in the same order, structured rather than re-parsed — the
               # alternative, reconstructing it from `after` in the consumer, is a second home for
               # the readiness arithmetic AND reads a DANGLING predecessor as satisfied, because a
               # predecessor with no `taskforce.csv` row of its own gets no output row here.
               "unmet-after": unmet_after,
               # D4: THE SEED, present on EVERY row (`[]` on a root and on a row nothing satisfies)
               # — same rule and same reason as `unmet-after`, `row-outcome` and
               # `undeclared-session` above: a key that appears only when it fires cannot be read
               # as a term, and an ABSENT key raises in a consumer where an empty list decides.
               # ⚠ THE FIELD NAME IS `seed` AND ITS VALUE IS AN ARRAY OF STRINGS. That is the
               # contract the daemon's seeding pass is written against (D1 + D4): it enqueues every
               # `READY` row and launches the seat with this list as its inputs. Renaming it or
               # boxing the strings breaks a consumer in another language that this file's tests
               # cannot see.
               # ⚠ ON A NON-`READY` ROW IT IS PARTIAL BY CONSTRUCTION and is NOT a launch input:
               # it carries the members that ARE satisfied so far. On a `READY` row every member is
               # satisfied by definition, so it is complete — which is the only row the contract
               # above is about.
               # ⚠ IT ASSERTS NOTHING ABOUT EXISTENCE. The paths are RESOLVED, not stat-ed: a
               # predecessor cannot reach `done` with a declared output missing (7.676 refuses that
               # check-out), so a second existence sweep here would be a second reader of the same
               # question, answering it later and from further away.
               "seed": seed,
               # THE RENEW GATE. `{state, why}` on a row whose disposition is `renew`, `None` on
               # every other row — present on EVERY row for the same rule and the same reason
               # `unmet-after`, `row-outcome` and `undeclared-session` are: a key that appears
               # only when it fires cannot be read as a term, and an ABSENT key raises in a
               # consumer where a null decides. It IS a term — `deferral_class`'s disposition limb
               # reads it to split `renewing` from `renew-blocked`, and that classifier is a pure
               # function of the row, so the state has to live ON the row.
               "renewal": ({"state": _rn_state, "why": _rn_why}
                           if value == "renew" else None),
               # 7.383: {raw member token -> its rendered state}, present on EVERY row for the
               # same reason `unmet-after` is — `{}` on a root, never a key that appears only when
               # it fires. It is what `--explain` prints, so the explain view and the reason
               # string can no longer disagree about one member: they read one computation.
                "after-render": render}
        # §2.1's boolean, READ OFF THE SAME HOISTED ROWS as `held-asks` above and not re-derived:
        # it used to spend one `node` subprocess PER SEAT on `seatWaitingOnOwner` while the hold
        # read a different surface entirely, so the row could print `waiting_on_owner: false` beside
        # `verdict: HELD`. One read, one answer, N seats.
        rec["waiting_on_owner"] = bool(rec["held-asks"])
        rec["launchable"] = ending_store.is_launchable(
            not unmet_after, value, None if value != "incomplete" else 1)
        if skew:
            rec["verdict"] = "SKEW"
            rec["reason"] = (f"awaiting-close.json={skew[0]} | sessions.csv={skew[1]}  "
                             f"⚠ ADJUDICATE — the two records of this seat's own ending "
                             f"disagree; nothing advances on either until a human rules")
        elif rec["held-asks"]:
            # W2. ABOVE the disposition branch on purpose — see the verdict list. The seat this
            # hold exists for is precisely a seat that CHECKED OUT with its question still open,
            # so reading `DONE` first would mask every case the hold was built for.
            _ha = rec["held-asks"]
            rec["verdict"] = "HELD"
            rec["reason"] = (
                f"OWNER-ASK HOLD — this seat has {len(_ha)} posted ask(s) to the owner still open "
                f"in the ending store ({', '.join(str(n) for n in _ha)}). NOT OFFERED, and its "
                f"dependents WAIT: a question the owner has not answered is a question the run has "
                f"not settled, whatever this seat's own check-out says. It lifts when the ask is "
                f"REAPED — an authorized reply in that exact thread closes the row and signals the "
                f"relaunch in ONE act (spec-state-store §2.8) — and on no other event. It advances "
                f"NO edge meanwhile")
        elif value is not None:
            rec["verdict"] = "DONE"
            rec["reason"] = f"check-out `{value}` ({source})"
            if value == "renew":
                # ── THE RENEW GATE (2026-08-18) ────────────────────────────────────────────────
                # `renew` USED TO READ `DONE` HERE, beside `exited`, and that is the defect: a
                # seat saying "I am coming back" and a seat whose harness died were one word to
                # every reader of this surface. The two states now have their own verdicts, and
                # the split is `renewal_state`'s — the ONE reader of the successor signal.
                #
                # ⚠ NEITHER VERDICT ADVANCES AN EDGE, and neither needs to be prevented from
                # doing so: `after_member_state` reads the raw `renew` VALUE off `term`, and
                # `renew` is not `done` in any of its arms. The verdict word is the REPORT axis.
                #
                # ⚠ BELOW `SKEW` AND `HELD`, exactly where the old `DONE` sat, and this branch
                # moved nothing above it. A renew is a claim about this seat's own ending, and a
                # contradiction about that ending (`SKEW`) or an unanswered owner ask (`HELD`)
                # still decides first — the ladder's order is untouched by this change.
                _rn_pending = rec["renewal"]["state"] == RENEW_PENDING
                rec["verdict"] = "RENEWING" if _rn_pending else "RENEW-BLOCKED"
                rec["reason"] += (
                    f" — IN PROGRESS, NOT AN ENDING. This seat asked to come back and a SUCCESSOR "
                    f"IS PENDING: {rec['renewal']['why']}. It advances NO edge (the work is not "
                    f"finished) and it is NOT a failure: nothing routes it to the leader as a "
                    f"crash and nothing reads it as an ending nobody ruled on. It leaves this "
                    f"verdict when the successor's OWN session row records an ending — or, if the "
                    f"successor stops being possible, by flipping to `RENEW-BLOCKED`, which is "
                    f"how a renewal that never arrives stops looking like one in progress"
                    if _rn_pending else
                    f" — ⚠ RENEWAL BLOCKED, AND THIS ROW IS THE ALARM. This seat asked to come "
                    f"back and NO SUCCESSOR IS POSSIBLE: {rec['renewal']['why']}. The lineage has "
                    f"HALTED — nothing will run under this seat's name on its own, so a reader "
                    f"who waits waits forever. NOT a clean check-out and NOT a harness death: it "
                    f"is a renewal that could not be placed, and it needs a human. A leader ruling "
                    f"that the work in fact concluded records that finding (`rule-disposition` "
                    f"was deleted [T2-R12, T1-R9]; no replacement ruling instrument is wired here "
                    f"yet); otherwise the goal watcher relaunches this seat on its next pass, "
                    f"because a non-terminal ending with no later sitting IS owed work. It "
                    f"advances NO edge meanwhile")
            elif value != "done":
                rec["reason"] += (f" — this seat advances NO edge; only `done` does"
                                  if value != "exited" else
                                  " — THE HARNESS TERMINATED; whether the work is done is NOT "
                                  "established. Routes to the leader, which investigates and "
                                  "either relaunches or flips the row to `done`. It advances "
                                  "NO edge meanwhile")
        elif active:
            rec["verdict"] = "RUNNING"
            rec["reason"] = f"roster: active since {row.get('checkin') or '(unstamped)'}"
        elif seat not in built:
            rec["verdict"] = "UNBUILT"
            rec["reason"] = "not in taskforce.csv or sessions.csv"
        elif seat in undeclared:
            # 7.237. `terminal(self)` is None here, and this branch is the ONE place that None is
            # read as something other than "has not finished yet" — because an ENDED row says the
            # opposite. Above `BLOCKED` on purpose (see the verdict list): a transient unmet edge
            # must never mask a concluded seat whose ending nobody declared.
            rec["verdict"] = "UNDECLARED"
            rec["reason"] = (
                f"session `{undeclared[seat]}` ENDED with an EMPTY disposition — this seat's work "
                f"CONCLUDED and nobody declared how it ended. NOT OFFERED: relaunching would "
                f"re-run finished work. This is a DEFECT FOR THE `leader` to investigate — it "
                f"either gets the ending declared or rules the row — and it is NOT a relaunch "
                f"instruction to anyone. Nothing here infers what the ending WAS: only the "
                f"occupant witnessed that. It advances NO edge meanwhile")
        elif rec["row-outcome"]["stop"]:
            # 7.224. THE REFUSAL ITSELF — not a warning beside the offer. The caller that filters
            # `verdict == "READY"` cannot be handed this seat even if it never reads the reason,
            # and a caller that does not know the value simply fails to match it. Both directions
            # are fail-safe; neither advances an edge.
            _ro = rec["row-outcome"]
            rec["verdict"] = "STOPPED"
            rec["reason"] = (
                f"store row {_ro['store-row']} carries "
                f"`row-outcome/{'`, `row-outcome/'.join(_ro['stop'])}` — the run has already "
                f"ruled this row concluded or held. NOT OFFERED: the row-outcome claim's subject "
                f"is the ROW, and it governs over every session-keyed surface. A terminal value "
                f"never lifts; a holding value lifts only when its named exit event fires and the "
                f"tag is cleared in that same act. It advances NO edge meanwhile")
        elif is_staff_seat(seat) and not staff_mail.get(seat):
            # W3 · THE ON-DEMAND CHAIR, NOT WOKEN. See the `staff_mail` hoist above for why mail is
            # a term at all. Placed LAST before the `after` arithmetic deliberately: every refusal
            # above names a state a staff chair can genuinely reach (a skew, a hold, a ruled row),
            # and each of those is the more informative reason. This is the CLEAN idle case.
            rec["verdict"] = "IDLE"
            rec["reason"] = (
                f"ON-DEMAND staff chair with NO mail — this seat holds no workflow node and is "
                f"spawned only to drain messages addressed to it. NOT OFFERED, and that is the "
                f"seat working: an empty sitting spends a launch to read an empty inbox. It wakes "
                f"the moment anything is addressed to `{seat}` (the session-closer's staff mail, a "
                f"routed FAIL, a seat's ask, a lifecycle alarm): D12 — UNREAD MAIL IS THE WAKE, "
                f"and the goal watcher (`engine/reconcile.js`, every 5 min) is what turns it into "
                f"a sitting. Nothing is minted and nothing can be lost. It advances NO edge "
                f"meanwhile")
        elif is_summoned_seat(seat):
            # D24 · THE SUMMONED SEAT, NOT OFFERED. Narrower than the staff-chair branch
            # above: mail is NOT a wake term. The daemon's `verdict == "READY"` filter must
            # never spawn this seat; a bot-tag / forward-path enqueue (which does not read
            # this verdict) is the summon. Conjunction admission is untouched — an explicit
            # `launch --only goal-master` still admits.
            rec["verdict"] = "IDLE"
            rec["reason"] = (
                f"ON-DEMAND summoned seat — this seat holds no workflow node and is spawned "
                f"only when the owner addresses it (a goal-channel message or `@rbtv` bot "
                f"tag). NOT OFFERED: minting it must not launch a sitting. It advances NO "
                f"edge meanwhile")
        else:
            # 7.273: `unmet` is built ONCE at the top of this iteration, for every row and not
            # only the ones that reach here — see the hoist above. The membership, the order and
            # the rendering below are byte-for-byte what this branch built for itself before.
            if unmet:
                rec["verdict"] = "BLOCKED"
                rec["reason"] = "after: " + " ".join(unmet)
            else:
                rec["verdict"] = "READY"
                # 7.383: rendered from `render`, the SAME per-member computation the unmet prose
                # spends — never a second `=done` literal that a later branch could contradict. A
                # bare member still reads `p=done`, byte-identical to before this change.
                rec["reason"] = ("after: " + " ".join(f"{p}={render[p]['state']}"
                                                      for p in preds)) if preds \
                    else "after: (root — no predecessors)"
        out.append(rec)
    # D22: THE `dead` TERM, AFTER the loop because it is a FIXPOINT OVER THE ROWS — a member is
    # dead when the seat it names is dead, and that seat's own row may be built after this one.
    # It reads `unmet-after` and `verdict`, which every row above now carries, and re-parses
    # nothing. See the block above `dead_after_entry` for what `dead` means and why it is a field.
    mark_dead_rows(out)
    return out


# ---------- 7.274 (A3): THE LAUNCH-ADMISSION PREDICATE ------------------------------------
#
# Spec: `planning/briefing-scoped-launch/launch-admission-spec.md` version 5, ACCEPTED at
# `runs/run-3/decisions.md#p-v5-RESPEC-ACCEPTED-at-d02432b0-all-lifts-fire` (that ANCHOR governs;
# the file's own internal banner is stale by authorship and the leader ruled it stays as-is).
#
# WHAT LIVES HERE AND WHY IT IS NOT INSIDE `cmd_launch`. These are the ROW-LEVEL terms of the
# admission decision — a pure function of one `ready_seat_rows` record and nothing else. They sit
# beside the home that PRODUCES those records so the two are read together, and so the self-test
# can drive them over a fixture without driving a launch. `cmd_launch` CALLS them; it re-derives
# nothing. A second computation of one fact is the defect class this run keeps filing (PRIN-11).
#
# ⚠ NO TERM HERE READS `verdict`. `no-class-clause`: the three ruled-legitimate relaunch lanes are
# structurally excluded from ever reading `READY`, so a `verdict`-keyed filter would decide the
# admission on a field whose value those lanes can never carry. What writing on FIELDS buys is the
# REPORT axis — eleven deferral classes where the verdict word gives one, so `exit-unruled` routes
# to the `leader` where `finished` does not, though all four disposition values read `DONE`.

# The disposition limb's own sub-partition. `RECORD_DISPOSITION_WRITER` closes this domain AT THE
# WRITE BOUNDARY; `terminal_disposition` does not re-validate at the READ, so a value outside it is
# a real edge and gets its own loud class rather than a closure this code did not measure. The
# self-test asserts the two key sets are equal, so a disposition value added without a class here
# goes RED instead of silently classing as `terminal-unenumerated`.
_DEFERRAL_BY_DISPOSITION = {"done": "finished", "renew": "renewing",
                            "revive": "revived", "exited": "exit-unruled",
                            # 7.676: its OWN class, never folded into `exit-unruled`. Both route
                            # to the leader, so folding them would look free — and it would erase
                            # the one distinction the value was minted to carry: `exit-unruled` is
                            # the KIT saying a harness died with the work UNKNOWN; `incomplete` is
                            # the SEAT saying the work is UNFINISHED. Same destination, opposite
                            # evidentiary weight, and only one of them has a reason attached.
                            "incomplete": "declared-incomplete",
                            # D32 (2026-08-20): its OWN class, never folded into
                            # `declared-incomplete`. The 7.676 argument directly above applies
                            # unchanged and is the reason two same-destination words must not
                            # merge: both route to the leader, so folding would look free — and it
                            # would erase the one distinction the word was minted to carry.
                            # `declared-incomplete` is the SEAT saying its work is unfinished;
                            # `claimed-unverified` is the SEAT claiming DONE with the kit unable to
                            # grade the claim. Same destination, opposite evidentiary weight, and
                            # only one of them is a statement about the WORK.
                            "unverified": "claimed-unverified"}

# The class → verdict mirror. It is a HAND-COPY of `ready_seat_rows`' own precedence, and it is
# made SELF-DETECTING by the self-test's row-P fixture rather than trusted: the fixture covers every
# REACHABLE pair of defer limbs, so transposing any two of them reds arm 1.
#
# ⚠ W2's `HELD` IS DELIBERATELY NOT A LIMB HERE, AND THAT IS A SCOPE STATEMENT, NOT AN OMISSION.
# The hold's consumer is the READY SURFACE — the ignite daemon's seeding door, a `verdict ==
# "READY"` filter. This map serves `coordinate launch`'s admission predicate, where the owner-ask
# hold is already enforced ONE door earlier and from the seat's own side: `cmd_checkout` REFUSES a
# `done` while the seat's ask to the owner is open. A held seat can therefore still be hand-launched
# by a human who types `launch --only <seat>`, which is a human overriding a hold in front of him,
# not the automatic advance the hold exists to stop. Making it a limb means an eighth limb and a
# 28-pair coverage set; do that only when a measured case needs it.
CLASS_TO_VERDICT = {"records-disagree": "SKEW", "finished": "DONE",
                    # THE RENEW GATE (2026-08-18). `renewing` read `DONE` and `renew-blocked` did
                    # not exist, so a seat coming back and a seat whose harness died were one word
                    # here too. `renewing` is IN PROGRESS — not terminal, not the failure class —
                    # and `renew-blocked` is a HALT that must look like one. Both still defer the
                    # launch: `conjunction_admits`' clause B is a single null test on
                    # `disposition`, and `renew` is not null, so NO admission moved with this
                    # split. What moved is the REPORT axis, which is what the class is for.
                    "renewing": "RENEWING", "renew-blocked": "RENEW-BLOCKED",
                    "revived": "DONE", "exit-unruled": "DONE", "terminal-unenumerated": "DONE",
                    # 7.676: `DONE` here is the ADMISSION verdict — "this row's session ENDED, so
                    # it is not a launch candidate" — and never a statement that the WORK is done;
                    # `exit-unruled` has read `DONE` on the same grounds since dag-11. The work's
                    # state is the CLASS, which is why the class is the thing that routes.
                    "declared-incomplete": "DONE",
                    # D32: `DONE` for the SAME reason `declared-incomplete` and `exit-unruled`
                    # read it — the ADMISSION verdict, "this row's session ENDED, so it is not a
                    # launch candidate". It says NOTHING about the work; the CLASS is what routes,
                    # and this class routes to the leader for a ruling (D33(b); `rule-disposition`,
                    # the verb that recorded one, was deleted [T2-R12, T1-R9]).
                    "claimed-unverified": "DONE",
                    "occupied": "RUNNING", "unbuilt": "UNBUILT", "undeclared-ending": "UNDECLARED",
                    "row-stopped": "STOPPED", "unmet-predecessor": "BLOCKED"}

# The seven defer LIMBS, in the home's own precedence order. SEVEN LIMBS, FOURTEEN CLASSES — they
# are not the same count and a reader computing `len(classes) == len(limbs)` gets every figure
# downstream wrong: the `disposition` limb alone produces eight (D32 added `claimed-unverified`).
ADMISSION_LIMBS = ("skew", "disposition", "active", "built", "undeclared", "stop", "unmet")

# limb → the class it names on a row that trips it, or None. ONE table read by the classifier, the
# transposition check and the coverage counter, so a limb cannot be defined three ways.
_LIMB_CLASS = {
    "skew":        lambda r: "records-disagree" if r["skew"] is not None else None,
    # THE RENEW GATE'S SPLIT lives here rather than in `_DEFERRAL_BY_DISPOSITION`, and that is
    # deliberate: that table's key set is asserted EQUAL to `RECORD_DISPOSITION_WRITER`'s, so
    # splitting a value there would be a silent widening of the closed set a seat may WRITE. No
    # disposition value is added by this change; one READ of `renew` becomes two classes, off the
    # row's own `renewal` field. A row predating the field (`.get`, not `[...]`) reads `None` and
    # takes the loud arm — the same fail-safe direction `renewal_from_entry` takes.
    "disposition": lambda r: (
        (("renewing" if (r.get("renewal") or {}).get("state") == RENEW_PENDING
          else "renew-blocked") if r["disposition"] == "renew"
         else _DEFERRAL_BY_DISPOSITION.get(r["disposition"], "terminal-unenumerated"))
        if r["disposition"] is not None else None),
    "active":      lambda r: "occupied" if r["active"] is True else None,
    "built":       lambda r: "unbuilt" if r["built"] is not True else None,
    "undeclared":  lambda r: "undeclared-ending" if r["undeclared-session"] is not None else None,
    "stop":        lambda r: "row-stopped" if r["row-outcome"]["stop"] else None,
    "unmet":       lambda r: "unmet-predecessor" if r["unmet-after"] else None,
}

# The FIELD each limb decided on, so a deferral names the value that decided it and not only the
# class word. "Never filter silently": a filter that removes without naming what it removed and why
# is indistinguishable from a filter that never ran.
_LIMB_FIELD = {"skew": "skew", "disposition": "disposition", "active": "active",
               "built": "built", "undeclared": "undeclared-session",
               "stop": "row-outcome.stop", "unmet": "unmet-after"}


def deferral_class_under(row, order):
    """The class this row defers with, under an ARBITRARY limb precedence. `None` == admitted.

    Parameterised on the order for ONE reason: the self-test transposes two limbs and asserts the
    class map stops mirroring the home's verdicts. A checker that could not re-order could not
    prove the mirror is real rather than coincidental on today's population."""
    for limb in order:
        cls = _LIMB_CLASS[limb](row)
        if cls:
            return cls
    return None


def deferral_class(row):
    """The class this row defers with under the TRUE precedence, or `None` when it admits.

    A PURE FUNCTION OF THE ROW. It reads no argument, no invocation shape and no caller state:
    an `exited` row classes `exit-unruled` however the tool was invoked, which is what makes the
    instrument (below) an instrument rather than a second reading of this function."""
    return deferral_class_under(row, ADMISSION_LIMBS)


def deferral_field(row):
    """(field-name, value) — the field that DECIDED this row's class, for the deferral line."""
    for limb in ADMISSION_LIMBS:
        if _LIMB_CLASS[limb](row):
            name = _LIMB_FIELD[limb]
            value = row["row-outcome"]["stop"] if limb == "stop" else row.get(name)
            return name, value
    return "", None


def conjunction_admits(row):
    """Clauses A–G of the admission boolean: the ORDINARY path, with no instrument in play.

    Every term is a NAMED FIELD of the row. Type safety is a property of the producer and is
    asserted there: `active`/`built` are real bools, `disposition` is never `""`, `row-outcome` is
    always a dict and always carries `stop`, `unmet-after` is present on every row (`[]` when
    clean) — an ABSENT key would raise here, which is why the producer's emit-on-every-row rule is
    a term of this boolean's safety and not a presentation choice."""
    return (row["skew"] is None                      # clause A
            and row["disposition"] is None           # clause B — VALUE-level, single null test
            and row["active"] is False               # clause C
            and row["built"] is True                 # clause D
            and row["undeclared-session"] is None    # clause E
            and row["row-outcome"]["stop"] == []     # clause F
            and row["unmet-after"] == [])            # clause G — 7.273's field


# ---- the limb-pair coverage instruments (self-test only; here because they are pure row math) ----
#
# ⚠ THE THREE SETS BELOW ARE SPELLED OUT AS EXPLICIT LITERAL MEMBERS, never as one set minus a
# computed predicate. A set derived by the same reasoning the assertion tests would pass any change
# to that reasoning — the guard-that-reads-its-own-constant defect. Pairs are canonical-ordered by
# `ADMISSION_LIMBS` index.
ALL_21_PAIRS = frozenset({
    ("skew", "disposition"), ("skew", "active"), ("skew", "built"), ("skew", "undeclared"),
    ("skew", "stop"), ("skew", "unmet"),
    ("disposition", "active"), ("disposition", "built"), ("disposition", "undeclared"),
    ("disposition", "stop"), ("disposition", "unmet"),
    ("active", "built"), ("active", "undeclared"), ("active", "stop"), ("active", "unmet"),
    ("built", "undeclared"), ("built", "stop"), ("built", "unmet"),
    ("undeclared", "stop"), ("undeclared", "unmet"),
    ("stop", "unmet"),
})

# 13 of 21. `(skew, disposition)` and `(skew, undeclared)` cannot BOTH hold on any row this home
# can produce, and every pair that includes `built` is unreachable once existence is the CSV
# registers: a `taskforce.csv` row is always in `registered_seats`, so `row["built"]` is True
# and the limb never trips.
#   (skew, disposition) — the only `return` that produces a skew tuple binds `None` as the
#       disposition, so a tripped `skew` FORCES the `disposition` conjunct to hold.
#   (skew, undeclared)  — skew requires a NON-EMPTY durable cell; `undeclared_endings` admits a
#       seat only when that SAME cell of that SAME row is EMPTY. Both cannot hold.
REACHABLE_PAIRS = frozenset({
    ("skew", "active"), ("skew", "stop"), ("skew", "unmet"),
    ("disposition", "active"), ("disposition", "undeclared"),
    ("disposition", "stop"), ("disposition", "unmet"),
    ("active", "undeclared"), ("active", "stop"), ("active", "unmet"),
    ("undeclared", "stop"), ("undeclared", "unmet"),
    ("stop", "unmet"),
})

# 14 of 21 — a DIFFERENT set from the one above, and the difference is the point. Coverage is
# bounded by what the home can PRODUCE; detection by what a re-ordering can be SEEN BY. A
# transposition re-orders the whole map, so a swap of two limbs is caught by any row tripping the
# lower one and anything ranked between them — no row need trip both. `(skew, undeclared)` is
# therefore DETECTABLE though unreachable. `(skew, disposition)` and every pair that includes
# `built` (the limb never trips on a registered taskforce row) are undetectable.
DETECTABLE_PAIRS = frozenset({
    ("skew", "active"), ("skew", "undeclared"), ("skew", "stop"),
    ("skew", "unmet"),
    ("disposition", "active"), ("disposition", "undeclared"),
    ("disposition", "stop"), ("disposition", "unmet"),
    ("active", "undeclared"), ("active", "stop"), ("active", "unmet"),
    ("undeclared", "stop"), ("undeclared", "unmet"),
    ("stop", "unmet"),
})


def tripped_limbs(row):
    """The set of defer limbs this row trips — ALL of them, not only the winning one."""
    return {limb for limb in ADMISSION_LIMBS if _LIMB_CLASS[limb](row)}


def covered_limb_pairs(rows):
    """Every canonical limb PAIR some row of `rows` trips simultaneously."""
    order = {limb: i for i, limb in enumerate(ADMISSION_LIMBS)}
    out = set()
    for row in rows:
        limbs = sorted(tripped_limbs(row), key=order.__getitem__)
        for i, x in enumerate(limbs):
            for y in limbs[i + 1:]:
                out.add((x, y))
    return frozenset(out)


def arm1_fails_under_transposition(rows, x, y):
    """True when swapping limbs `x` and `y` in the precedence makes arm 1 go RED on `rows`.

    THIS IS THE META-CHECK. Arm 1 alone proves the class map agrees with the home TODAY; only this
    proves the agreement is load-bearing — that a re-ordering would be CAUGHT rather than passing
    unnoticed on a population that never trips both limbs."""
    order = list(ADMISSION_LIMBS)
    i, j = order.index(x), order.index(y)
    order[i], order[j] = order[j], order[i]
    for row in rows:
        cls = deferral_class_under(row, tuple(order))
        ok = (cls is None and row["verdict"] == "READY") or \
             (cls is not None and CLASS_TO_VERDICT[cls] == row["verdict"])
        if not ok:
            return True
    return False


# ---------- D2 (2026-08-19): the daemon's seed-refusal surfacing (`coordinate surface-refusal`) --
#
# WHAT IT IS: the ignite daemon lands ONE cage-admission refusal on the goal's own bus. The
# measured failure (G-owner-console-0818-2030): a seat refused at every 10s seed pass for hours,
# journal-only — no surface an operator reads ever said so. The engine may not write coordination
# files itself (the runtime boundary: neither side reads or writes the other's files), so the
# refusal crosses as a command — the daemon runs `coordinate surface-refusal`, it never
# opens a coordination file itself.
#
# IDEMPOTENT PER (seat, reason), and that is the whole verb: the seed pass repeats forever, so a
# plain `send` would append one row per tick. The dedup marker (`seed-refusal: <seat> <key>`,
# key = sha256 of the reason) rides the body's FIRST LINE; the scan and the append share one
# `coord_lock` hold so two concurrent passes cannot both observe "not yet surfaced" and both
# append.
def cmd_surface_refusal(args):
    """(daemon) surface ONE seed-time refusal on the goal bus, once per (seat, reason)."""
    gate(args, "surface-refusal")
    seat = args.seat
    reason = (args.reason or "").strip()
    if not reason:
        refuse("input",
               "--reason is the refusal text being surfaced; an empty one would append a bus row "
               "that tells the operator nothing and dedup against every other empty refusal.", 2)
    base = base_dir(args)
    sender = resolve_agent(args)
    key = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:12]
    marker = f"seed-refusal: {seat} {key}"
    as_json = bool(getattr(args, "json", False))
    with coord_lock(base):
        _path, blocks = load_messages(base)
        dup = next((b for b in blocks if any(marker in ln for ln in b["lines"])), None)
        if dup is None:
            num = _append_message_unlocked(
                base, sender, "owner", "note",
                # D5/D9 (seed-gates, 2026-08-19): the body line is GENERIC — this verb now
                # carries every seed-pass refusal class (declared-output admission, lane
                # reach, goal-not-live), and the verbatim reason below names which one.
                f"{marker}\n\nNOT seeded — the seeding pass refused it before the queue. "
                f"The daemon repeats this check every seed pass; this row is written "
                f"once. The refusal, verbatim:\n\n{reason}")
            status = "surfaced"
        else:
            num, status = dup["num"], "already-surfaced"
    payload = {"status": status, "seat": seat, "key": key, "num": num}
    print(json.dumps(payload, indent=2, sort_keys=True) if as_json else
          f"{seat}: {status} as bus row #{num} (key {key})")


# ---------- LE-10 (2026-08-19): the renewal answer, exported read-only (`renewal-state`) ----------
#
# WHY A VERB EXISTS FOR A ONE-LINE ANSWER: `evaluateExit` (ignite/engine/attached-execution.js) was
# the last reader collapsing stuck-vs-unfinished — it could end a console run `blocked` on a seat
# whose `--renew` successor was mid-hand-over. The single source of renewal truth is
# `renewal_state` (rbtv 3b43bda1), a PYTHON function with, by doctrine, no JS reader deriving its
# own answer: JS may TRANSPORT the answer, never re-derive it. This
# verb is that transport's far end — a thin print over `renewal_state`, no logic of its own, so the
# reader count stays at one.
#
# READ-ONLY, and `register=False` says so structurally: resolving the package normally
# (re-)registers the run tag, which is a write, and this verb's whole contract is that it makes
# none (dag-10's own pattern, `base_dir`'s note). No identity gate for `ready-seats`' reason: an
# answer about the run's own recorded state, computable by anyone who can read the package.
def cmd_renewal_state(args):
    """(engine) ONE seat's renewal answer — READ-ONLY, verbatim from `renewal_state`."""
    state, why = renewal_state(base_dir(args, register=False), args.seat)
    if getattr(args, "json", False):
        print(json.dumps({"seat": args.seat, "state": state, "why": why},
                         indent=2, sort_keys=True))
    else:
        print(f"{args.seat}: {state} — {why}")


def cmd_ready_seats(args):
    """The ready-SEAT frontier, computed from disk. READ-ONLY: launches nothing, writes nothing,
    messages nobody."""
    rows = ready_seat_rows(args)
    target = getattr(args, "explain", None)
    if target:
        rec = next((r for r in rows if r["seat"] == target), None)
        if rec is None:
            refuse("input",
                   f"'{target}' has no row in this run's taskforce.csv, so there is no predicate "
                   f"to evaluate for it. Seats in this run: "
                   f"{', '.join(r['seat'] for r in rows) or '(none)'}\n"
                   f"The whole frontier: {coord_invocation(args)} ready-seats", 2)
        # TERM BY TERM, in the predicate's own order, each with the value that decided it — so a
        # reader learns WHICH term held the seat, never merely that something did.
        print(f"{c('seat:', C_LABEL)} {rec['seat']}    {c(rec['verdict'], C_LABEL)}")
        print(f"  terminal(self)      = {rec['disposition'] or 'None'}"
              f"{' (' + rec['source'] + ')' if rec['source'] else ''}"
              f"   -> not itself finished: {rec['disposition'] is None}")
        print(f"  no ACTIVE roster row                                 -> {not rec['active']}")
        print(f"  descriptor on disk                                   -> {rec['built']}")
        # 7.237: rendered on EVERY seat, not only the ones it trips — the term that decided a
        # verdict is unreadable if the clean value is invisible. It names the session, because
        # "an ending was not declared" sends the reader hunting for WHICH one.
        _u = rec.get("undeclared-session")
        print(f"  last ended session declared an ending                -> {_u is None}"
              + (f"   ⚠ `{_u}` ENDED with an EMPTY disposition — work CONCLUDED, ending never "
                 f"declared. Defect -> `leader`, NOT a relaunch" if _u else ""))
        # D42: rendered on EVERY seat, `-> True` being the term CLEARING — same rule as the line
        # above. ⚠ IT IS NOT A TERM OF THE VERDICT: the line reports a FACT ABOUT THE ROW, and the
        # verdict printed at the top is computed without it. A held row blocks exactly what it
        # blocked before; what a hold changes is the goal watcher, which stops re-waking the leader.
        print("  no leader HOLD on the last ended row                  -> True")
        # 7.224: rendered on EVERY seat, not only the ones it trips — same rule as the line above,
        # same reason. The NOTE is always printed because "no stop-state" and "nothing was read"
        # are the two readings a reader must never have to guess between, and an unenumerated
        # `row-outcome/*` value is named here rather than acted on.
        _ro = rec.get("row-outcome") or {"values": [], "stop": [], "note": "(not computed)"}
        _other = [v for v in _ro["values"] if v not in _ro["stop"]]
        print(f"  bound store row carries no stop-state                -> {not _ro['stop']}"
              f"   [{_ro['note']}]"
              + (f"   ⚠ STOP-STATE: `row-outcome/"
                 + "`, `row-outcome/".join(_ro["stop"]) + "` — the run has ruled this row "
                 "concluded or held. NOT OFFERED" if _ro["stop"] else "")
              + (f"   (also carries `row-outcome/"
                 + "`, `row-outcome/".join(_other) + "`, which is not an enumerated stop-state "
                 "and does NOT suppress)" if _other else ""))
        # W2: THE OWNER-ASK HOLD, rendered on EVERY seat — `-> True` is the term CLEARING, and this
        # one is a term of the verdict on every row (unlike the grant below, which is an instrument
        # that either exists or does not).
        _ha = rec.get("held-asks") or []
        print(f"  no unanswered ask to the owner                        -> {not _ha}"
              + (f"   ⚠ OWNER-ASK HOLD: {', '.join(str(n) for n in _ha)} posted and open —"
                 f" dependents WAIT until an authorized reply in that thread reaps the ask"
                 if _ha else ""))
        if not rec["after"]:
            print("  every `after` predecessor is `done`                   -> True (root — none)")
        # 7.383: READ FROM THE ROW, NOT RE-DERIVED. This loop used to look each member up in the
        # OUTPUT ROWS BY NAME and read that row's `disposition` — a second home for the readiness
        # arithmetic, and one carrying the very name-lookup defect 7.383 closes: a guarded token
        # matches no output row, so this printed `<no check-out>` on its own account regardless of
        # what the loop above had computed. `after-render` is that computation, and `unmet-after`
        # is the same pass's verdict on the member.
        for p in rec["after"]:
            _m = (rec.get("after-render") or {}).get(p) or {"state": "<no check-out>",
                                                            "met": False}
            print(f"  after `{p}` = {_m['state']}   -> {_m['met']}")
        # D22: rendered on EVERY seat, `-> True` being the term CLEARING — same rule as the
        # `undeclared-session` and owner-ask lines above. `dead` is derived from the ruling rows in
        # `guard-values.csv` at read time and is never stored anywhere.
        print(f"  its `after` can still become satisfied                -> {not rec.get('dead')}"
              + ("   ⚠ DEAD — this seat can NEVER run and is NOT pending work. See the reason"
                 if rec.get("dead") else ""))
        print(f"  {c('reason:', C_LABEL)} {rec['reason']}")
        return
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        width = max([len(r["seat"]) for r in rows] or [4])
        for r in rows:
            print(f"{r['verdict']:<8}  {r['seat']:<{width}}  {r['reason']}")
        counts = {}
        for r in rows:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        print(f"\n{len(rows)} seat(s): "
              + " · ".join(f"{k}={counts[k]}" for k in sorted(counts)))
        # D22: NAMED, and OMITTED when zero — exactly as `counts` above omits a verdict no seat
        # holds, and a second line rather than a term of the census because `dead` is NOT a
        # verdict (a dead seat is also counted in `BLOCKED`), so folding it in would make the
        # census sum wrong.
        _dead = [r["seat"] for r in rows if r.get("dead")]
        if _dead:
            print(f"dead={len(_dead)}: {', '.join(_dead)}"
                  f"   ⚠ these are BLOCKED FOREVER, not pending — a mode-variant branch the lane "
                  f"did not take, or something downstream of one. They are NOT owed work: no "
                  f"consumer may count them pending, retry them or alarm on them. Each row's "
                  f"reason names why")
    # ── Q2a — A SKEW BLOCKS ITS OWN SEAT, NEVER THE WHOLE GOAL (owner-ruled 2026-08-18) ───────
    #
    # THE DEFECT THIS CLOSES, measured 2026-08-18. This was an unconditional `sys.exit(1)` on any
    # SKEW row, and the one JS consumer (`engine/seeding.js#readySeats`) runs the verb under
    # `execFileSync` — where a non-zero exit lands in the catch and the COMPLETE answer is thrown
    # away. ONE disputed seat on `meet-transcript-summarizer` therefore froze 65 healthy siblings
    # for 4.5 hours across 1,704 refusals, one every ~10s, with zero owner-facing signal.
    #
    # ⚠ THE SKEW IS UNCHANGED AND JUST AS LOUD. `terminal_disposition` still refuses to pick a
    # winner, the row still reads `SKEW` carrying both values with their sources, the dependents
    # still read `BLOCKED`, and the census still counts it. Only the BLAST RADIUS shrank: the
    # per-seat containment already lived on the ROWS, and the exit status was a second, goal-wide
    # copy of it that no row asked for.
    #
    # ⚠ AND THIS IS NOT A GENERAL LOOSENING. Every `refuse(...)` on this path still exits non-zero,
    # because "I could not ask" (an unreadable package, bad argv, a crash) and "one seat of many is
    # disputed" are different claims — a consumer that cannot tell them apart is the defect above
    # in reverse. A caller that genuinely wants the old whole-goal fail-close asks for it BY NAME
    # with `--fail-on-skew`; the rows say the same thing to anyone reading the JSON.
    if getattr(args, "fail_on_skew", False) and any(r["verdict"] == "SKEW" for r in rows):
        sys.exit(1)


def peer_windows(seats, me):
    """Every shared-window name declared by descriptors OTHER than `me`'s.

    OTHER than its own, and that exclusion is the whole point: validating a value against the union
    of all descriptors INCLUDING the seat under test is vacuous — the seat's own typo would appear
    in the set and authorize itself. Nearly shipped that way."""
    return {w["window"] for w in seats
            if w["window"] and w["window"] != "yes" and w["agent"] != me}


def window_drift(w, peers):
    """'' when the seat's `window:` is placeable, else the reason it is a probable typo.

    THE DEFECT THIS CATCHES, and it is drift that looks like success: nothing validated the value,
    and an unrecognised window name does not fail — `launch_seat` finds no window of that name and
    cheerfully OPENS ONE. So `window: controll` places the seat "correctly" into furniture nobody
    ordered, and the room silently grows a window named after a misspelling.

    NO LAYOUT IS HARDCODED HERE, deliberately and by ruling (leader #382): the ruled four-window
    organization belongs to ONE campaign, and freezing its names into a tool every run shares would
    refuse every launch in a room organized differently. That is the mistake `SPECIAL_CASE_SEATS`
    was demoted for — a MANDATE cannot be expressed as a name list — repeated in the same file.

    So the signal is a NEAR MISS, not membership: a name no peer declares is a legitimately new
    window and passes, while a name that is one edit away from a window peers DO declare is the
    typo. Same idiom, same cutoff, as this file's recipient-typo refusal (F5), and it refuses only
    where it can name the intended value."""
    name = (w or {}).get("window") or ""
    if not name or name == "yes" or name in peers:
        return ""
    near = difflib.get_close_matches(name, sorted(peers), n=1, cutoff=0.8)
    if not near:
        return ""
    return (f"window '{name}' is declared by no other seat, and it is one edit from '{near[0]}', "
            f"which is. An unrecognised window is NOT refused by tmux — it silently OPENS a new "
            f"one, so this would place the seat into a window named after a typo.\n"
            f"declared by peers: {', '.join(sorted(peers))}\n"
            f"Fix the descriptor, or launch with --force if '{name}' is genuinely a new window.")
