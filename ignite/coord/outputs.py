import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---- D3 (2026-08-18): THE ONE DECLARED-OUTPUTS RESOLVER ----------------------------------------
# The io-spec `## Outputs` block in the seat.md BODY is the single declared-outputs surface.
# Two readers consume it: this function (D4 seed computation + 7.676 done-contract grading) and
# `engine/cage-admission.js#parseDeclaredOutputs` (the caged-launch admission gate). They are TWO
# PARSERS OF ONE GRAMMAR, deliberately — a cross-language subprocess call would put node on
# coord.py's runtime path (probes and caged runs execute without it) and a per-checkout process
# spawn on the hot path — held equivalent by ONE shared fixture set,
# `outputs-resolver-fixtures.json` beside this file, exercised by BOTH sides' scheduled checks
# (this file's selftest; `engine/probes/probe-outputs-resolver.js`). Change the grammar in both
# files and the fixtures in the same commit, or one side's check goes red — that is the
# anti-drift mechanism, and it is mechanical, not a prose promise.
_IOSPEC_BLOCK = re.compile(r"<io-spec\b[\s\S]*?</io-spec>")
_IOSPEC_OUTPUTS_SECTION = re.compile(r"##[ \t]*Outputs[ \t]*([\s\S]*?)(?=\n##[ \t]|\Z)")
# A backticked token that looks like a path: contains a `/` and carries an extension —
# `edge-runner-job.py#_PATHISH`'s grammar, the same BYTES the JS gate matches. ⚠ Deliberately NOT
# widened to slashless tokens (`plan.md`) or bare directories (`build/`): every widening here
# widens the admission gate's refusal surface identically (a token this matches is a token the
# cage gate must place), and prose blocks backtick file NAMES that are not outputs. A slashless
# declaration is written `./plan.md` — resolved at the seat's own `cwd` (D4/RS-28) AND, since D90
# (2026-08-22), ALSO at the goal root (`declared_outputs`' own widening, `resolved_outputs`
# unchanged) — a file at the goal folder's ROOT, with no subdirectory to name, has no OTHER
# sanctioned spelling; a directory is declared by a file inside it.
_IOSPEC_PATHISH = re.compile(r"`([^`\s]*/[^`\s]*\.[A-Za-z0-9]{1,6})`")
# D36 (2026-08-20): THE ONE TYPED NON-FILE OUTPUT. An `## Outputs` bullet whose SCHEMA is
# literally `chat` declares a product that is CONVERSATION — a verdict row on the bus, an answer,
# a queue-request — and therefore has no path to check. It is a DECLARATION, not an absence: the
# seat said what it produces and the kit can read that claim. Both consumers treat it as declared
# (the check-out admits the `done`; materialize's zero-token check stays quiet), while
# `admitDeclaredOutputs` sees the same zero path tokens it always saw — unchanged.
# ⚠ SCHEMA POSITION ONLY, deliberately: the word `chat` occurs in ordinary output prose all over
# this catalog ("...posted to the chat bridge"), and matching it loose would silently exempt real
# file producers. The bullet must OPEN with it — `- Schema: chat …`.
# Mirrored in `engine/cage-admission.js#CHAT_SCHEMA` and pinned by the shared fixture set.
_IOSPEC_CHAT = re.compile(r"^[ \t]*[-*][ \t]*\**Schema:?\**:?[ \t]*`?chat`?\b",
                          re.MULTILINE)


def iospec_outputs(text):
    """(declared, tokens, chat) for ONE seat.md's full text — the shared resolver's Python half.

    `declared` is whether an `## Outputs` section EXISTS inside an `<io-spec>` block, carried
    separately from the tokens because a PROSE section yielding ZERO tokens is its own loud
    condition — the check-out records `outputs-undeclarable`, never a silent `none-declared`
    (D3 planner extension: 23 of 26 meet-transcript-summarizer dones read `none-declared`
    while their seats carried prose `## Outputs` blocks the retired frontmatter key's readers
    could not see). `chat` (D36, 2026-08-20) is the THIRD answer: a bullet opening
    `- Schema: chat` declares a NON-FILE product, so ZERO tokens is the honest reading and not
    an undeclarable one — the check-out admits that `done`. No file, no block, no section ->
    (False, [], False)."""
    block = _IOSPEC_BLOCK.search(text or "")
    if not block:
        return False, [], False
    section = _IOSPEC_OUTPUTS_SECTION.search(block.group(0))
    if not section:
        return False, [], False
    return (True, _IOSPEC_PATHISH.findall(section.group(1)),
            bool(_IOSPEC_CHAT.search(section.group(1))))


# The retirement tripwire's second shape: the indented YAML block-list spelling of the same
# retired key (7.711's old malformed class) — still detected, so it refuses as RETIRED rather
# than silently declaring nothing.
_OUTPUTS_BLOCK_YAML = re.compile(r"^outputs:[ \t]*\r?\n[ \t]*-[ \t]", re.MULTILINE)


def _fm_outputs_defect(fm):
    """Why this descriptor's frontmatter is refused on the outputs surface — "" when clean.

    D3: the ONLY defect left is carrying the RETIRED `outputs:` frontmatter key at all, in any
    shape. Detected on the descriptor because the key is wrong the moment it is written; refused
    LOUDLY at `declared_outputs` (the seat's own check-out) and at materialize-seats.py's
    materialize gate — never read as a declaration, never dropped silently."""
    if FM_KEY["outputs"].search(fm) or _OUTPUTS_BLOCK_YAML.search(fm):
        return ("it carries the RETIRED `outputs:` frontmatter key (D3, 2026-08-18: the io-spec "
                "`## Outputs` block in the seat.md body is the ONE declared-outputs surface). "
                "Declare each output there as a backticked goal-relative token carrying a `/` "
                "and an extension — `seats/<seat>/plan.md` for a file in the seat's own cwd, or "
                "`./name.md` for a file with no subdirectory (checked at the seat's own cwd AND, "
                "D90, the goal root) — and DELETE the key")
    return ""


def briefing_files(wdir):
    """Every briefing path in discovery order: flat <roster>/*.md, then <roster>/*/agent.md and
    <roster>/*/seat.md (seat.md is the KG run-folder form — seats/<seat>/seat.md; agent.md the
    legacy workers/ form)."""
    if not wdir.is_dir():
        return []
    flat = sorted(p for p in wdir.glob("*.md"))
    folder = sorted(list(wdir.glob("*/agent.md")) + list(wdir.glob("*/seat.md")))
    return flat + folder


def briefing_frontmatters(wdir):
    """agent-name -> (frontmatter text, briefing path), for every briefing in workers/."""
    out = {}
    for p in briefing_files(wdir):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm_end = text.find("\n---", 3)
        if fm_end == -1:
            continue
        fm = text[:fm_end]
        m = FM_KEY["agent"].search(fm)
        if m:
            out[m.group(1)] = (fm, p)
    return out


def observer_sets(args):
    """(observers, auto_wake) — built-in defaults plus per-run briefing declarations."""
    observers, auto = set(DEFAULT_OBSERVERS), set(DEFAULT_AUTO_WAKE)
    for agent, (fm, _p) in briefing_frontmatters(workers_dir(args)).items():
        if _fm_yes(fm, "observer"):
            observers.add(agent)
        if _fm_yes(fm, "auto-wake"):
            auto.add(agent)
    return observers, auto


def _fm_list(fm, key):
    """The comma-separated values of `key`, or None when the key is absent.

    None and the empty list are DIFFERENT answers here and the distinction is load-bearing: absent
    means "undeclared, keep today's behaviour", while `broadcast: none` means "declared, and the
    answer is nothing". Collapsing them would make an explicit narrowing indistinguishable from
    never having said anything."""
    m = FM_KEY[key].search(fm)
    if not m:
        return None
    return [v.strip() for v in m.group(1).split(",") if v.strip()]


def inbox_decls(args):
    """{seat: {"senders": frozenset, "broadcast": scope}} — each seat's DECLARED inbox topology,
    read from its OWN descriptor. Keys appear only when the descriptor declares them.

        senders:   leader, master        the ONLY seats whose messages reach this one
        broadcast: none | all | a,b      which `to: all` TYPES reach it (G-20, declared)
        relays:    master                ROLE TOKENS this seat carries the relay path for

    `relays:` is what makes the other two usable at all for a role word. `senders: leader, master`
    is the owner's ruled wording, and `leader` resolves only because that role's name happens to BE
    a seat name; `master` is a FUNCTION and matched nobody, so the ruled bound admitted a sender
    that does not exist and refused the seat actually carrying the owner channel. Measured before
    it was built (`probe_master_bound.py`): M2 and M4 red, M5 green — the bound was sound and the
    identity layer was missing.

    Two owner rulings bound an inbox to named senders (`r-cos-bounded-inbox` for the
    chief-of-staff, `r-engineer-contact` for the engineer: leader + master, a third sender is a
    breach). Until this existed both were enforced by the SEAT DECLINING — the message still
    arrived, still spent the seat's context, and a breach was visible only if the seat noticed and
    said so.

    DERIVED, never a kit-side name list, for the same reason `observer:`/`auto-wake:` are. A name
    list in the kit encodes ONE campaign's role vocabulary into a tool every run shares: another
    run's `engineer` is narrowed by accident and its differently-named system seat is not.
    `SPECIAL_CASE_SEATS` named its members while its own comment described a MANDATE ("serve the
    SYSTEM or the ROOM") — which is exactly how the chief-of-staff came to be omitted from the set
    whose definition described it. A mandate cannot be expressed as a name list, so the next such
    seat is forgotten identically. The seat descriptor already IS where topology is declared
    (harness, model, observer, auto-wake, ctx-refresh); inbox scope belongs beside them.

    ABSENCE IS TODAY'S BEHAVIOUR on both keys, and no descriptor in any package declares either —
    so this ships INERT: it changes no seat's inbox until a descriptor says otherwise.
    """
    decls = {}
    for agent, (fm, _p) in briefing_frontmatters(workers_dir(args)).items():
        d = {}
        named = _fm_list(fm, "senders")
        if named:
            d["senders"] = frozenset(named)
        relays = _fm_list(fm, "relays")
        if relays:
            d["relays"] = frozenset(v.lower() for v in relays)
        raw = _fm_list(fm, "broadcast")
        if raw is not None:
            low = [v.lower() for v in raw]
            if low == ["all"]:
                d["broadcast"] = None            # every type, explicitly
            elif low == ["none"]:
                d["broadcast"] = frozenset()     # no broadcast at all
            else:
                d["broadcast"] = frozenset(low)  # exactly these types
        if d:
            decls[agent] = d
    return decls


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def file_stamp():
    return datetime.now().strftime("%Y%m%d-%H%M")


# ---- the DATED EXECUTION STAMP (7.607 E2b; `d-extinguishment-design-lock` item 5 / D5) --------
#
# THE DELIMITER THE RUN ID USED TO BE. With runs extinguished a goal has ONE workspace and its
# files are single and append-only, so successive EXECUTIONS of the same goal write into the same
# `sessions.csv`, the same `messages.md`, the same watcher state. The stamp is what tells them
# apart at read time — `YYYY-MM-DDx`, e.g. `2026-08-09a`, monotonic within a day, a NEW letter for
# each boot and a fresh `a` on a new date.
#
# ⚠ IT IS AN IDENTITY, NOT A STATUS, AND THE DIFFERENCE IS THE WHOLE 7.608 LESSON. It says WHICH
# execution a row belongs to; it never says whether anything is running. Liveness has exactly one
# answer — the derived lease (item 1) — and nothing here may be consulted for it. A stamp file
# left behind by a crashed execution is correct data about a past execution, not a claim.
#
# ⚠ ONE HOME FOR THE RULE. `mint_execution` is called at ONE moment — when the goal's room is
# CREATED, i.e. a boot (`workflow_launcher.ensure_session`'s create arm, via the `execution --mint`
# verb) — and everything else READS through `current_execution`. Joining an existing room mints
# nothing, which is what makes a re-fire of the same boot idempotent.
EXECUTION_FILE = "execution"
EXECUTION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})([a-z]+)$")


def _execution_path(base):
    return Path(base) / EXECUTION_FILE


def _next_letter(letters):
    """`a`->`b` … `z`->`aa`->`ab`; a pure odometer so a 27th boot in one day is still ordered."""
    chars = list(letters)
    i = len(chars) - 1
    while i >= 0:
        if chars[i] != "z":
            chars[i] = chr(ord(chars[i]) + 1)
            return "".join(chars)
        chars[i] = "a"
        i -= 1
    return "a" + "".join(chars)


def current_execution(base):
    """This goal's CURRENT execution stamp. Reads the marker; mints today's first when there is
    none, so a package that predates the stamp (or a bare `--base` fixture) still yields a usable,
    dated id rather than an empty cell. A marker whose content is not a stamp is treated as absent
    — a corrupt delimiter must not become a delimiter."""
    try:
        raw = _execution_path(base).read_text(encoding="utf-8").strip()
    except OSError:
        raw = ""
    if EXECUTION_RE.match(raw):
        return raw
    return datetime.now().strftime("%Y-%m-%d") + "a"


def mint_execution(base):
    """Mint and record the NEXT execution stamp for this goal. Returns it.

    Called at BOOT and nowhere else. Same day -> the next letter after the recorded one; a new day
    (or no marker, or an unreadable one) -> that date's `a`. The write is atomic, like every other
    state write in this file."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        raw = _execution_path(base).read_text(encoding="utf-8").strip()
    except OSError:
        raw = ""
    m = EXECUTION_RE.match(raw)
    stamp = today + (_next_letter(m.group(2)) if (m and m.group(1) == today) else "a")
    Path(base).mkdir(parents=True, exist_ok=True)
    atomic_write(_execution_path(base), stamp + "\n")
    return stamp


RUNS_INDEX = Path.home() / ".config" / "rbtv" / "coordinate-runs.json"


def write_runs_index(idx):
    """Persist the registry. Best-effort: a read-only HOME must never break coordination."""
    try:
        RUNS_INDEX.parent.mkdir(parents=True, exist_ok=True)
        RUNS_INDEX.write_text(json.dumps(idx, indent=1), encoding="utf-8")
    except OSError:
        pass


def load_runs_index(prune=True):
    """The run-tag registry, with dead entries dropped (T5): a package folder that no longer
    exists (a /tmp package, a deleted run) polluted every `--run` error listing. Rewrites the
    file only when pruning actually changed it; every failure is silent."""
    try:
        idx = json.loads(RUNS_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(idx, dict):
        return {}
    if not prune:
        return idx
    # 7.607 E2b (design-lock item 8): this registry re-keys BY GOAL NAME, because a package IS a
    # goal folder and its tag is its folder name. Every entry written before the cutover points at
    # a `<goal>/runs/run-N` compartment and is STALE BY CONSTRUCTION — the tag is a run ordinal,
    # not a goal — so it is dropped here rather than left to resolve `--run run-1` at a path whose
    # meaning changed under it. Dropped by SHAPE (parent named `runs`), never by existence: the
    # legacy folders survive on disk until the live-goal migration, so an existence prune would
    # keep every one of them.
    alive = {tag: path for tag, path in idx.items()
             if Path(path).is_dir() and Path(path).parent.name != "runs"}
    if alive != idx:
        write_runs_index(alive)
    return alive


def register_run(pkg):
    """Auto-register a package under its folder-name tag so later calls can say
    `--run <tag>` (or nothing, from inside the package) instead of the full path.

    A tag is never STOLEN: when it already points at a DIFFERENT package that still exists on
    disk, the second same-named package registers nothing and says nothing. Re-pointing it
    silently redirected `--run <tag>` — and every wake and hint built from it — at the wrong
    run (observed live, two packages sharing a folder name). Silence is deliberate: the loser
    needs no warning, because `coord_invocation` sees the tag does not resolve to its own path
    and emits the full `--package` form instead. A tag whose path is GONE was already dropped by
    load_runs_index's prune, so the new package takes it."""
    idx = load_runs_index()
    tag = Path(pkg).name
    held = idx.get(tag)
    if held == str(pkg):
        return
    if held and Path(held).is_dir():
        return
    idx[tag] = str(pkg)
    write_runs_index(idx)


def discover_package_from(cwd):
    """Nearest ancestor (cwd included) that IS a package — identified by its own STRUCTURE
    (coordination/ + a roster dir: seats/ in the KG form, workers/ in the legacy form). Seats' cwd
    is their seat folder, so a bare `coordinate <cmd>` resolves for them with no arguments at all.

    7.607 E2b: the package is the GOAL FOLDER now, and this function needed no change to follow it
    — it never asked for a `runs/run-N` shape, only for the two directories a package carries.
    That is why the structural predicate was worth having."""
    p = Path(cwd).resolve()
    for cand in (p, *p.parents):
        if (cand / "coordination").is_dir() and (
                (cand / "seats").is_dir() or (cand / "workers").is_dir()):
            return cand
    return None


def package_dir(args, register=True):
    """Resolution order: --package path > --run tag (registry) > COORD_PACKAGE env >
    cwd walk-up. Every successful resolution (re-)registers the tag."""
    pkg = getattr(args, "package", None)
    if not pkg and getattr(args, "run", None):
        pkg = load_runs_index().get(args.run)
        if not pkg:
            known = ", ".join(sorted(load_runs_index())) or "(none registered yet)"
            print(f"error: unknown run tag '{args.run}' — known: {known}", file=sys.stderr)
            sys.exit(2)
    if not pkg:
        pkg = os.environ.get("COORD_PACKAGE")
    if not pkg:
        pkg = discover_package_from(Path.cwd())
    if not pkg:
        known = ", ".join(sorted(load_runs_index())) or "(none registered yet)"
        print("error: no package — pass --run <goal> or --package <abs-goal-folder>, or "
              f"invoke from inside a package. Known goals: {known}", file=sys.stderr)
        sys.exit(2)
    pkg = Path(pkg).resolve()
    if register:
        register_run(pkg)
    return pkg


def base_dir(args, register=True):
    # `register` (dag-10) exists for the READ-ONLY commands: resolving a package normally
    # (re-)registers the run tag, which is a WRITE, and a command whose whole contract is "this
    # writes nothing" cannot make one. It is a parameter here rather than a second resolver in the
    # read-only command, so both paths keep using the one resolution order (PRIN-11).
    if getattr(args, "base", None):
        base = Path(args.base).resolve()
    else:
        base = package_dir(args, register=register) / "coordination"
    set_injection_context(base=base)  # 7.39: the primitives get no args; this is the one chokepoint
    return base


def workers_dir(args, register=True):
    # `register` exists for the SAME reason `base_dir`'s does (dag-10, see its note): resolving a
    # package normally (re-)registers the run tag, which is a WRITE, and a command whose whole
    # contract is "this writes nothing" cannot make one. DEFAULT TRUE so every existing caller
    # keeps registering exactly as before; only a read-only caller passes False.
    if getattr(args, "workers_dir", None):
        return Path(args.workers_dir).resolve()
    pkg = package_dir(args, register=register)
    seats = pkg / "seats"  # KG run-folder form wins when present; legacy workers/ otherwise
    if seats.is_dir():
        return seats
    return pkg / "workers"


def coord_invocation(args):
    """The exact command string agents use — embedded in wakes and launch prompts. Prefers
    the per-machine `coordinate` PATH symlink (it IS a CLI — seats should not carry the
    script's full path) and the short `--run <tag>` form (auto-registered); falls back to
    the full forms where symlink/registry are absent."""
    import shutil
    script = Path(__file__).resolve()
    cli = "coordinate" if shutil.which("coordinate") else f"python3 {script}"
    if getattr(args, "base", None):
        return f"{cli} --base {Path(args.base).resolve()}"
    # ⚠ `register=False` (F17): this function BUILDS A STRING. Resolving the package normally
    # (re-)registers the run tag, which is a WRITE — and this builder is called from REFUSAL text,
    # including F17's entry bound, whose whole claim is that it refused and acted on nothing. A
    # string builder that writes makes that claim false. The cost is stated rather than hidden: on
    # a package that has never been registered the advice falls back to the long `--package` form
    # instead of `--run <tag>`, because there is no tag to offer yet. Every command that actually
    # READS the package still registers it through `base_dir`.
    pkg = package_dir(args, register=False)
    if load_runs_index().get(pkg.name) == str(pkg):
        return f"{cli} --run {pkg.name}"
    return f"{cli} --package {pkg}"


