#!/usr/bin/env python3
"""bindings — the CASTING SHEET tool: author the per-seat harness·model·effort file that turns a
workflow into a taskforce (owner-ruled 2026-08-10).

WHAT A BINDINGS FILE IS, AND WHERE IT LIVES
-------------------------------------------
A workflow is the program: an ordered set of seats (`workflows/<w>/<w>.csv` inside a mirrored
component). A TASKFORCE is its running instance. The bindings file is what casts one into the
other — per seat, WHICH harness, WHICH model, WHICH effort, plus the lane fields the descriptor
carries. It is read ONCE, by `ignite/team-kit/materialize-seats.py --bindings`, at the moment a
goal's seats are materialized. Nothing boot-reads it, no daemon holds it open: **every write here
is a plain file write and no restart is ever needed** — which is why this tool, unlike its
`goal-launch-delay` / `master-profile` siblings, has no staged-inbox/daemon-fire second half.

    .rbtv/config/modules/{module}/{component}/bindings/{code}.json   ← the canonical path
                                                                       (owner ruling 1, filed
                                                                        module-first by D15)

The pre-D15 spelling `.rbtv/config/bindings/{module}/{component}/{code}.json` still READS — every
verb falls back to it and WARNS with the new path named — so a deployment that has not moved its
files yet keeps working loudly rather than breaking silently.

DEPLOYMENT CONFIG, NOT A COMPONENT DEFINITION. The mirror (`.rbtv/mirror/<module>/<component>/`)
carries what a component IS; a casting sheet is what THIS WORKSPACE decided to spend on running it,
so it lives under `.rbtv/config/` with the rest of the deployment's knobs.

`{code}` IS THE WORKFLOW'S CODE — the common seat-id prefix its manifest rows already carry
(`plan-interviewer`, `plan-splitter`, … → `plan`), DERIVED from the manifest and never typed
(ruling 2). A manifest whose rows do not share one prefix is refused rather than guessed at.

ONE FILE PER WORKFLOW (ruling 3), created on first use and reused by every later goal until someone
edits it. No per-goal copies and no templates lying around: `check_bindings_cover` demands the
`seats` key set EQUAL the manifest's, so a stale copy is a refusal at the next materialize, and the
only way to keep N copies honest is to not have them.

THE VALIDATION SOURCE, AND WHY IT IS THIS ONE
---------------------------------------------
`catalog` is BOTH the owner-facing "what can I cast?" surface and the ONE list `set` validates
against — one derivation, two consumers, so the printed answer and the enforced answer can never
disagree. It is composed from exactly two measured sources, and nothing else:

  1. WHICH harness+model pairs exist — `ignite/config/spawn-profiles.yaml` `profiles:`, which
     r-seats-only-architecture makes "ONE PROFILE PER HARNESS+MODEL … nothing else is identity".
     That IS this workspace's spawnable set; a roster frozen in this file would admit a model the
     box cannot spawn or refuse one it can. The harness is the profile's argv[0]; the model is the
     literal its `exec` argv PINS (`--model` / `-m`).
     ⚠ THE MODEL VOCABULARY IS THE PROFILE'S PIN, VERBATIM — `claude-fable-5` for `claude-fable`,
     `claude-opus-5` for `claude-opus`: every profile pins a FULL model id (owner ruling
     2026-08-10, which eliminated the earlier alias/full-id asymmetry in the config itself). The
     claude binary honours both an alias and a full model id (`claude --help`: "an alias … or a
     model's full name"), so BOTH forms would run; but only the pinned literal joins a bindings row
     back to a profile row, and inventing the other form here would be a second mapping of the same
     fact — the drift DEC-1 § Shared profile source exists to forbid. A caller passing an alias is
     REFUSED with the catalog's models printed, never silently rewritten.

  2. WHETHER a pair has an effort dial — the profile's own `effort:` block. `effort: { inert: true }`
     is a MEASUREMENT under G-270 ("a harness whose dial does not exist says so"), so an inert
     profile has NO dial here and refuses any effort number.

  …and the LEVELS of a dial that exists come from THE PROFILE'S OWN `effort.rungs` list — the one
  copy, read straight off `spawn-profiles.yaml` (`profile_effort` below, which is ALSO the
  master-profile capability's `effort_ladder`: one function, imported, not two that agree). A
  bindings value is passed to the harness LITERALLY (`coord.py#harness_command`), and the rung
  NUMBER indexes that list.

  ⚑ PER MODEL, NEVER PER HARNESS (owner ruling 2026-08-11: "effort level is not per harness, is per
  model"). A profile IS one harness+model pair, so its own block is already the right granularity:
  `claude-haiku` is single-mode and declares `effort: { inert: true }` while `claude-fable` declares
  five rungs — same harness, different ladders. The per-harness `NATIVE_EFFORT` table this paragraph
  used to point at could not express that and is DELETED; the duplication it warned about is gone
  with it, and so is the kimi blocker that deferred the merge (two lanes may spell rung N however
  each needs to — the NUMBER is what the sheet stores, and a number has no spelling).

Every catalog row is finally passed through `coord.py#validate_seat` — the SAME predicate
`materialize-seats.py` applies to the whole batch before any write (its F6 gate, which imports it
for exactly this reason: "NEVER re-implement the predicate here"). A profile whose harness or model
that predicate rejects is listed as NOT CASTABLE with its reason rather than silently dropped.

THE VERBS
---------
  catalog                                  what this workspace can cast, with each dial's numbers
  inspect  <workflow.csv>                  every manifest seat: id, definition files, staffing
                                           hints, and which seats are still uncast
  scaffold <workflow.csv>                  create the file at the canonical path, every manifest
                                           seat present, casting values null (create-only)
  set      <workflow.csv> <seat> <harness> <model> <effort-number>
                                           cast one seat; the NUMBER is a 1-based index into that
                                           harness's native ladder and the FILE stores the native
                                           STRING — the number is input abstraction only

⚠ A FULL json.load/json.dump ROUND TRIP IS CORRECT HERE and is deliberately unlike this capability's
siblings, which line-edit. Those edit `spawn-profiles.yaml`, a hand-authored document whose comments
are its documentation. This file is machine-owned end to end: this tool creates it, this tool is the
only writer, and nobody hand-authors one any more (ruling 4).
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

_IGNITE = Path(__file__).resolve().parents[3]
DEFAULT_PROFILES = _IGNITE / "config" / "spawn-profiles.yaml"
TEAM_KIT = _IGNITE / "team-kit"

# The harness's OWN ordered effort levels — the strings the binary itself accepts, which is what a
# bindings value becomes. Measured, each with its source; never the profile translation table.
# ── THE LADDER IS THE PROFILE'S OWN, AND IT IS PER MODEL ────────────────────────────────────────
#
# `NATIVE_EFFORT` — a per-HARNESS tuple of rung words — is DELETED (owner ruling 2026-08-11:
# "effort level is not per harness, is per model"). It was the second copy of a fact
# `spawn-profiles.yaml` already carries per profile, and the two spellings could not both be right:
# a profile IS one harness+model pair, so `claude-haiku` (single-mode, `effort: {inert: true}`) and
# `claude-fable` (five rungs) share a harness and have different ladders. Keyed by harness, the
# table had to pick one and was wrong for the other.
#
# It also mis-zeroed opencode. Its entry was `()` on a 2026-07-09 note reading "opencode forwards
# `--variant` unvalidated … no honoured ladder at all" — a conclusion about the HARNESS drawn from
# one model, when `opencode run --help` calls `--variant` "model variant (provider-specific
# reasoning effort)". Provider-specific is per model by definition. ⚠ THAT MEASUREMENT HAS SINCE
# BEEN MADE (2026-08-11) and the seven `opencode-*` profiles now declare REAL ladders, enumerated
# per model from opencode's own registry — `opencode models <provider> --verbose`, whose `variants`
# keys ARE the ladder, so no live model call is needed. The per-model claim is not a nicety: the
# ladders are NOT uniform even within one provider (`zai-coding-plan/glm-5.2` is `[high, max]` with
# no low or medium; `google/gemini-flash-latest` is `[low, high]` with no medium, while its sibling
# `gemini-3.1-pro-preview` has three). A harness-keyed table could not have expressed any of that.
# ⚠ AND THE GUARD MUST STAY UPSTREAM, HERE: an invalid `--variant` is accepted by opencode
# SILENTLY — exit 0, no warning — so a wrong rung would fail invisibly. Nothing invalid may ever
# reach the binary, which is why `set` range-checks against the ladder at authoring time rather
# than trusting a return code at launch.
#
# Reading the rungs off the profile block makes the numbering ONE object end to end: this file's
# 1-based `<effort-number>`, the daemon's `resolveEffort` rung, and the seat's declared `effort:`
# are the same index into the same list.


def profile_effort(profile, profiles_path=DEFAULT_PROFILES):
    """This profile's ordered rungs. `[]` means an INERT dial; `None` means NO dial at all.

    THE ONE PYTHON READER OF THE LADDER. `master_profile.effort_ladder` IS this function, imported —
    not a second implementation that agrees. It had been one, and the two DID NOT agree on identical
    bytes: this file searched the whole profile block for `effort: { inert: true }` while its sibling
    line-scanned and returned on whichever of `inert` / `rungs:` appeared FIRST, so a `rungs:` line
    sitting ABOVE an inert declaration read as INERT here and as a FIVE-RUNG LADDER there (measured
    2026-08-11; moving that one line below flipped it back, which is what made ORDER the cause).

    The three-way answer is load-bearing and is the SIBLING's contract, kept because it is the
    richer one (G-270): `[]` ACCEPTS a rung and applies nothing, while `None` cannot translate one
    at all and refuses. A two-way `()` collapsed those and could not say which.

    ⚠ READING IS NOT WRITING, and the earlier note here confused them. `yaml.safe_load` destroys
    nothing — only DUMPING would. The asymmetry this capability's siblings actually live under is:
    reads of `spawn-profiles.yaml` are PARSES, writes to it stay line-precise edits, because the
    document is hand-authored and its comments are its documentation. A scrape bought nothing on the
    read side and cost this drift: `rungs:` written as a YAML block sequence (`rungs:` / `  - low`)
    is read correctly by the authoritative `launch-profiles/profiles.js#loadConfig` and was invisible
    to BOTH scrapers (also measured 2026-08-11). One parser, one answer.

    `inert: true` alongside `rungs:` answers INERT regardless of line order — `profiles.js`
    refuses that combination at load, so it is unreachable in a config the daemon boots; answering
    it deterministically is what keeps line order from ever mattering again.
    """
    doc = yaml.safe_load(Path(profiles_path).read_text(encoding="utf-8")) or {}
    block = (doc.get("profiles") or {}).get(profile)
    effort = block.get("effort") if isinstance(block, dict) else None
    if not isinstance(effort, dict):
        return None                                 # no profile, or a profile with no dial
    if effort.get("inert") is True:
        return []
    rungs = effort.get("rungs")
    return [str(r) for r in rungs] if isinstance(rungs, list) and rungs else None


# The lane fields `scaffold` prefills. They are CONSTANTS of the materialize lane, not casting
# choices: `cwd-mode: seat-folder` is the only ruled cwd, `agent_type: staff` is what a workflow
# seat is, `mode:` is the DESCRIPTOR mode (materialize admits only one-shot|interactive — NOT the
# manifest's Modality column, which a seat carries via its own `human-interactive:` frontmatter),
# and `ctx-refresh` is a lane number. An author who wants different ones edits the file; the point
# of prefilling is that a scaffolded file is materializable the moment its casting is filled in.
LANE_DEFAULTS = {"cwd-mode": "seat-folder"}
LANE_PER_SEAT = {"agent_type": "staff", "mode": "interactive", "ctx-refresh": 35}

CASTING_KEYS = ("harness", "model", "effort")


class Refusal(Exception):
    """A refusal names what was rejected and what held instead — never a bare status."""


# ─────────────────────────────────────────────────────── the workflow → {module, component, code}

def resolve_workflow(workflow_csv):
    """Everything the canonical path needs, derived from the manifest's own location.

    A mirrored workflow manifest sits at exactly
    `<ws>/.rbtv/mirror/<module>/<component>/workflows/<w>/<w>.csv` — the shape
    `materialize-seats` resolves through `<catalog-root>/<component>/workflows/…`. Anything else
    refuses: a path this function had to guess about would put the bindings file somewhere the next
    reader looks for in vain."""
    p = Path(workflow_csv).resolve()
    if not p.is_file():
        raise Refusal(f"{p} is not a file — name the workflow manifest CSV itself")
    parts = p.parts
    try:
        mirror_at = len(parts) - 1 - parts[::-1].index("mirror")
    except ValueError:
        raise Refusal(f"{p} does not sit under a `.rbtv/mirror/` tree — this tool derives the "
                      f"module and component from the manifest's own location, and a path outside "
                      f"the mirror carries neither")
    tail = parts[mirror_at + 1:]
    if len(tail) != 5 or tail[2] != "workflows":
        raise Refusal(f"{p} is not at <mirror>/<module>/<component>/workflows/<w>/<w>.csv (got "
                      f"{'/'.join(tail)}) — refusing to guess which segment is the component")
    workspace = Path(*parts[:mirror_at - 1])       # …/<ws>/.rbtv/mirror → <ws>
    module, component = tail[0], tail[1]
    seats = manifest_seats(p)
    return {
        "manifest": p, "workspace": workspace, "module": module, "component": component,
        "component_dir": p.parents[2], "catalog_root": p.parents[3],
        "workflow": tail[3], "seats": seats, "code": workflow_code(seats),
    }


def manifest_seats(manifest):
    """The manifest's seat ids, in file order. Column 0 (`Seat/workflow`) and nothing else — the
    same column materialize resolves rows from."""
    with open(manifest, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh) if r and r[0].strip()]
    if len(rows) < 2:
        raise Refusal(f"{manifest} carries no seat rows under its header")
    seats = [r[0].strip() for r in rows[1:]]
    dupes = sorted({s for s in seats if seats.count(s) > 1})
    if dupes:
        raise Refusal(f"{manifest} names seat(s) {', '.join(dupes)} more than once — a bindings "
                      f"file is a mapping and could not carry both")
    return seats


def workflow_code(seats):
    """The workflow's CODE = the seat-id prefix every manifest row already carries (ruling 2).

    DERIVED, never typed: the code is the bindings FILENAME, so a typed one would file a casting
    sheet under a name the manifest does not agree with, and nothing would ever notice.

    ⚠ EXACTLY FOUR ASCII LETTERS (owner ruling 2026-08-10) — the shape being minted registry-side
    as `workflow code`. Refused here, loudly and by name, because this is the ONE place the code is
    ever computed: a five-letter prefix that slipped through would name a bindings file, a seat-id
    family and a registry record that disagree with the ruling forever after, and renaming seats
    after a taskforce exists is not a rename this tool can do for you."""
    prefixes = {s.split("-", 1)[0] for s in seats}
    if len(prefixes) != 1 or not prefixes.pop().strip():
        by = sorted({s.split("-", 1)[0] for s in seats})
        raise Refusal(f"the manifest's seat ids do not share ONE prefix (found {', '.join(by)}) — "
                      f"the workflow code IS that shared prefix and this tool refuses to pick one "
                      f"of several. Name the seats consistently, or file the casting sheet by hand "
                      f"knowing what the next reader will look for.")
    code = seats[0].split("-", 1)[0]
    if len(code) != 4 or not code.isascii() or not code.isalpha():
        raise Refusal(f"the workflow code `{code}` is {len(code)} character(s) — a workflow code "
                      f"MUST be exactly four ASCII letters (owner ruling 2026-08-10). The code is "
                      f"the shared seat-id prefix, so fix it in the manifest's `Seat/workflow` "
                      f"column (`plan-strategist`, `plan-designer`, …), not here.")
    return code


def bindings_path(wf, config_root=None):
    """The casting sheet's canonical path — MODULE-FIRST since owner ruling D15.

    BACKWARD COMPAT, deliberately loud: a deployment whose sheets still sit at the pre-D15
    `<config>/bindings/<module>/<component>/<code>.json` keeps working — every verb operates on the
    old file and WARNS with the new path named. Silence here would let a deployment sit
    un-migrated forever; a refusal would take the channel master's own knob down mid-migration."""
    root = Path(config_root) if config_root else wf["workspace"] / ".rbtv" / "config"
    new = root / "modules" / wf["module"] / wf["component"] / "bindings" / f"{wf['code']}.json"
    old = root / "bindings" / wf["module"] / wf["component"] / f"{wf['code']}.json"
    if not new.exists() and old.is_file():
        print(f"WARN: {old} is the PRE-MIGRATION casting-sheet path. This run reads it, but MOVE "
              f"it to {new} — owner ruling D15 files deployment config module-first at "
              f".rbtv/config/modules/<module>/<component>/bindings/<code>.json.", file=sys.stderr)
        return old
    return new


# ─────────────────────────────────────────────────────────────────────── the catalog

def _profile_blocks(profiles_path):
    """The `profiles:` section as {name: [block lines]}.

    ponytail: a line scan, not a YAML parse — it needs the block's LINES (`_exec_argv` reads the
    `argv:` list positionally off them), which a parse discards. The EFFORT question left this scan
    for `profile_effort`'s parser precisely because a scan answered it wrongly; this one is kept
    deliberately, not by inertia. Ceiling: a profile declared at a non-standard indent or with a
    quoted key is invisible. Upgrade path: PyYAML, now imported by this module anyway."""
    lines = Path(profiles_path).read_text(encoding="utf-8").splitlines()
    at = next((i for i, ln in enumerate(lines) if ln.rstrip() == "profiles:"), None)
    if at is None:
        raise Refusal(f"{profiles_path} declares no root key `profiles:` — refusing to validate "
                      f"against a set this file does not carry")
    blocks, current = {}, None
    for ln in lines[at + 1:]:
        if ln.strip() and not ln.startswith(" ") and not ln.lstrip().startswith("#"):
            break                                   # the next root key ends the section
        m = re.match(r"^  ([A-Za-z0-9][A-Za-z0-9._-]*):\s*$", ln)
        if m:
            current = m.group(1)
            blocks[current] = []
        elif current is not None:
            blocks[current].append(ln)
    if not blocks:
        raise Refusal(f"the `profiles:` section of {profiles_path} declares no profiles — refusing "
                      f"to validate against an empty set, which would refuse EVERY casting")
    return blocks


_QUOTED = re.compile(r'"([^"]*)"')


def _exec_argv(block):
    """The profile's `exec:` argv tokens. The list opens after `argv:` and closes on the first `]`."""
    out, collecting = [], False
    for ln in block:
        if not collecting:
            if re.match(r"^\s*argv:", ln):
                collecting = True
            else:
                continue
        out.extend(_QUOTED.findall(ln))
        if "]" in ln:
            break
    return out


def catalog(profiles_path=DEFAULT_PROFILES):
    """Every harness+model this workspace can cast, with each one's effort numbers.

    THE ONE derivation: `catalog` prints it and `set` enforces it, so the surface an agent reads and
    the surface that refuses it are the same object."""
    validate_seat = _coord_validate_seat()
    rows = []
    for name, block in _profile_blocks(profiles_path).items():
        argv = _exec_argv(block)
        if not argv:
            continue                                # a profile with no exec: half spawns nothing
        harness = Path(argv[0]).name
        model = ""
        for flag in ("--model", "-m"):
            if flag in argv[:-1]:
                model = argv[argv.index(flag) + 1]
                break
        # ONE call answers both questions. The second `inert` regex that used to live here was a
        # third opinion on the same bytes, disagreeing with `profile_effort` by construction: it
        # could report a dial INERT while the levels beside it listed five rungs.
        levels = profile_effort(name, profiles_path)
        reason = validate_seat({"agent": name, "harness": harness, "model": model})
        rows.append({"profile": name, "harness": harness, "model": model,
                     "effort-levels": list(levels or []), "castable": not reason,
                     "not-castable-because": reason or None,
                     "effort-dial": "inert (the profile declares `effort: { inert: true }` — G-270: "
                                    "a harness whose dial does not exist says so)" if levels == []
                                    else ("none — this profile declares no effort ladder"
                                          if levels is None else None)})
    return rows


def castable(profiles_path=DEFAULT_PROFILES):
    """{(harness, model): row} — the enforced set."""
    return {(r["harness"], r["model"]): r for r in catalog(profiles_path) if r["castable"]}


def _coord_validate_seat():
    """The launch-time harness+model predicate, IMPORTED from coord.py — never re-implemented.

    Exactly the move `materialize-seats.py#_coord_validate_seat` makes (its F6 gate), and for the
    identical reason: a second copy of the predicate is drift, and this tool's whole job is to write
    a file that predicate will accept."""
    if str(TEAM_KIT) not in sys.path:
        sys.path.insert(0, str(TEAM_KIT))
    try:
        from coord import validate_seat
    except Exception as exc:
        raise Refusal(f"cannot import validate_seat from {TEAM_KIT / 'coord.py'} — {exc}; refusing "
                      f"rather than re-implementing the predicate materialize-seats gates on")
    return validate_seat


# ─────────────────────────────────────────────────────────────────────── inspect

def _seat_catalog(catalog_root):
    """Every `seats.csv` row under the catalog root, keyed by seat-id. Catalog resolution is
    ROOT-WIDE (materialize merges across it), so a seat cataloged in a sibling component still
    resolves — the planning-deprecated lane's `ledger-groomer` was exactly that case."""
    out = {}
    for csv_path in sorted(Path(catalog_root).glob("*/seats.csv")):
        with open(csv_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                sid = (row.get("seat-id") or "").strip()
                if sid and sid not in out:
                    out[sid] = dict(row, __component=csv_path.parent)
    return out


_FM_HINT = re.compile(r'^staffing-recommendations:\s*"?(.*?)"?\s*$', re.M)


def inspect(workflow_csv, config_root=None):
    wf = resolve_workflow(workflow_csv)
    seats_cat = _seat_catalog(wf["catalog_root"])
    path = bindings_path(wf, config_root)
    cast = {}
    if path.is_file():
        cast = (json.loads(path.read_text(encoding="utf-8")) or {}).get("seats") or {}
    out = {"workflow": wf["workflow"], "module": wf["module"], "component": wf["component"],
           "code": wf["code"], "manifest": str(wf["manifest"]), "bindings": str(path),
           "bindings-exists": path.is_file(), "seats": []}
    for seat in wf["seats"]:
        row = seats_cat.get(seat)
        entry = {"seat": seat}
        if not row:
            entry["definition"] = None
            entry["unresolved"] = (f"no seats.csv row under {wf['catalog_root']} — materialize "
                                   f"would refuse this seat")
        else:
            comp = row["__component"]
            entry["definition"] = str(comp / "prompts" / f"{(row.get('executor') or '').strip()}.md")
            entry["task"] = str(comp / "tasks" / f"{(row.get('task') or '').strip()}.md")
            hint = (row.get("staffing-hints") or "").strip()
            source = "seats.csv staffing-hints"
            if not hint:
                # The catalog row's hints OVERRIDE the prompt's per pairing; where the row is empty
                # the prompt frontmatter's `staffing-recommendations` IS the advisory in force, and
                # printing sixteen blanks instead would hide the only hint that exists.
                fm = Path(entry["definition"])
                m = _FM_HINT.search(fm.read_text(encoding="utf-8")) if fm.is_file() else None
                hint, source = (m.group(1) if m else ""), "prompt frontmatter staffing-recommendations"
            entry["staffing-hints"] = hint or None
            entry["staffing-hints-source"] = source if hint else None
        b = cast.get(seat) or {}
        entry["cast"] = {k: b.get(k) for k in CASTING_KEYS} if b else None
        entry["uncast"] = not all(b.get(k) for k in CASTING_KEYS)
        out["seats"].append(entry)
    out["uncast"] = [s["seat"] for s in out["seats"] if s["uncast"]]
    extra = [s for s in cast if s not in wf["seats"]]
    if extra:
        out["extra-seats"] = extra
        out["warning"] = (f"the bindings file names {', '.join(extra)}, which the manifest does "
                          f"not — materialize refuses `bindings-extra-seat`")
    return out


# ─────────────────────────────────────────────────────────────────────── scaffold / set

def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def scaffold(workflow_csv, config_root=None, dry_run=False):
    """Create the casting sheet: every manifest seat present, casting values null.

    CREATE-ONLY, like every other create in this lane (`rbtv goal scaffold`, materialization
    itself). A file that already exists holds castings somebody made; overwriting it would be a
    silent re-cast of a taskforce that may already have run."""
    wf = resolve_workflow(workflow_csv)
    path = bindings_path(wf, config_root)
    if path.exists():
        raise Refusal(f"{path} already exists — this verb is create-only. ONE bindings file per "
                      f"workflow is reused by every later goal (ruling 3); change a seat with "
                      f"`set`, and read the current state with `inspect`.")
    doc = {
        "_what": (f"The casting sheet for the `{wf['workflow']}` workflow of "
                  f"{wf['module']}/{wf['component']} — one entry per manifest seat of "
                  f"{wf['manifest'].name}, read ONCE by materialize-seats.py --bindings when a "
                  f"goal's taskforce is materialized. Scaffolded by `rbtv-bindings`; authored only "
                  f"through that tool."),
        "_code": (f"`{wf['code']}` is this workflow's CODE — the seat-id prefix every manifest row "
                  f"carries — and it is this file's name. Derived from the manifest, never typed."),
        "defaults": dict(LANE_DEFAULTS),
        "seats": {seat: dict(LANE_PER_SEAT,
                             **{k: None for k in CASTING_KEYS},
                             component=str(wf["component_dir"]) + "/")
                  for seat in wf["seats"]},
    }
    if not dry_run:
        _write(path, doc)
    return {"ok": True, "action": "created" if not dry_run else "dry-run", "bindings": str(path),
            "code": wf["code"], "seats": len(wf["seats"]),
            "uncast": list(wf["seats"]),
            "note": "every seat is UNCAST — materialize would refuse `effort-missing` until each "
                    "one is `set`"}


def set_seat(workflow_csv, seat, harness, model, effort_number,
             config_root=None, profiles_path=DEFAULT_PROFILES, dry_run=False):
    wf = resolve_workflow(workflow_csv)
    if seat not in wf["seats"]:
        raise Refusal(f"'{seat}' is not a seat of {wf['manifest']}. Its {len(wf['seats'])} seats "
                      f"are: {', '.join(wf['seats'])}. Refused HERE because materialize refuses a "
                      f"`bindings-extra-seat` for the WHOLE batch, at goal-creation time, where "
                      f"nobody is holding the file.")
    path = bindings_path(wf, config_root)
    if not path.is_file():
        raise Refusal(f"{path} does not exist — `scaffold {workflow_csv}` first. `set` edits one "
                      f"seat of an existing sheet; it never mints the sheet, so a typo'd workflow "
                      f"path cannot quietly create a second casting sheet nobody reads.")

    known = castable(profiles_path)
    row = known.get((harness, model))
    if row is None:
        same = sorted(m for (h, m) in known if h == harness)
        raise Refusal(
            f"{harness}/{model} is not a castable pair. "
            + (f"The castable models for harness `{harness}` are: {', '.join(same)}. "
               if same else
               f"No profile declares harness `{harness}`. Castable harnesses: "
               f"{', '.join(sorted({h for h, _ in known}))}. ")
            + f"The set comes from `profiles:` in {profiles_path} — the model is the literal each "
              f"profile's exec argv PINS, and this tool never rewrites one spelling into another. "
              f"Run `catalog` to see every pair with its effort numbers.")

    levels = row["effort-levels"]
    if effort_number is None:
        if levels:
            raise Refusal(f"{harness}/{model} has an effort dial with {len(levels)} levels "
                          f"({', '.join(levels)}) — name one by number, 1..{len(levels)}. "
                          f"materialize refuses `effort-missing` on a seat with no effort.")
        effort = ""
    else:
        if not levels:
            raise Refusal(f"{harness}/{model} has NO effort dial ({row['effort-dial']}), so effort "
                          f"number {effort_number} names nothing. Omit the number: a stored value "
                          f"nothing honours is a knob that turns and does nothing.")
        if not 1 <= effort_number <= len(levels):
            raise Refusal(f"effort {effort_number} is outside 1..{len(levels)} for {harness}: "
                          + ", ".join(f"{i}={lv}" for i, lv in enumerate(levels, 1)))
        effort = levels[effort_number - 1]

    doc = json.loads(path.read_text(encoding="utf-8"))
    entry = dict(doc.get("seats", {}).get(seat) or {})
    before = {k: entry.get(k) for k in CASTING_KEYS}
    entry.update({"harness": harness, "model": model})
    # The FILE stores the harness's own string; the number is input abstraction and is never stored.
    if effort:
        entry["effort"] = effort
    else:
        entry.pop("effort", None)
    doc.setdefault("seats", {})[seat] = entry
    if not dry_run:
        _write(path, doc)
    uncast = [s for s, e in doc["seats"].items()
              if not all((e or {}).get(k) for k in CASTING_KEYS)]
    return {"ok": True, "action": "set" if not dry_run else "dry-run", "bindings": str(path),
            "seat": seat, "before": before,
            "after": {"harness": harness, "model": model, "effort": effort or None},
            "effort-number": effort_number, "effort-ladder": levels,
            "uncast": uncast}


# ─────────────────────────────────────────────────────────────────────── cli

def _print_catalog(rows):
    print("harness+model this workspace can cast — from `profiles:` in spawn-profiles.yaml, "
          "gated by coord.py#validate_seat\n")
    w = max(len(f"{r['harness']}/{r['model']}") for r in rows)
    for r in sorted(rows, key=lambda r: (not r["castable"], r["harness"], r["model"])):
        pair = f"{r['harness']}/{r['model']}".ljust(w)
        if not r["castable"]:
            print(f"  --  {pair}  NOT CASTABLE — {r['not-castable-because']}  [{r['profile']}]")
            continue
        dial = ("  ".join(f"{i}={lv}" for i, lv in enumerate(r["effort-levels"], 1))
                if r["effort-levels"] else f"no effort dial — {r['effort-dial']}")
        print(f"  ok  {pair}  {dial}   [{r['profile']}]")
    print("\nthe effort NUMBER is the index; the file stores the harness's own level string")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="rbtv-bindings",
        description="author the casting sheet that turns a workflow into a taskforce — the "
                    "per-seat harness/model/effort file materialize-seats.py reads as --bindings")
    # Options hang off the VERBS, not the root parser: as root options argparse accepts them only
    # BEFORE the verb, and the sibling capability's first live fire died on exactly that
    # (`error: unrecognized arguments: --config`).
    prof = argparse.ArgumentParser(add_help=False)
    prof.add_argument("--profiles", default=str(DEFAULT_PROFILES),
                      help="the spawn-profiles document the castable set is derived from")
    root = argparse.ArgumentParser(add_help=False)
    root.add_argument("--config-root",
                      help="config root (default: <workspace>/.rbtv/config, derived from the "
                           "manifest's own location); the sheet sits at "
                           "<config-root>/modules/<module>/<component>/bindings/<code>.json")
    sub = p.add_subparsers(dest="verb", required=True)

    c = sub.add_parser("catalog", parents=[prof],
                       help="every harness+model this workspace can spawn, with each effort dial's "
                            "numbers")
    c.add_argument("--json", action="store_true")

    i = sub.add_parser("inspect", parents=[root],
                       help="every manifest seat: definition files, staffing hints, casting state")
    i.add_argument("workflow")
    i.add_argument("--json", action="store_true")

    s = sub.add_parser("scaffold", parents=[root],
                       help="create the bindings file at the canonical path, every seat uncast")
    s.add_argument("workflow")
    s.add_argument("--dry-run", action="store_true")

    t = sub.add_parser("set", parents=[root, prof], help="cast one seat")
    t.add_argument("workflow")
    t.add_argument("seat")
    t.add_argument("harness")
    t.add_argument("model")
    t.add_argument("effort", nargs="?", type=int,
                   help="1-based index into the harness's native effort ladder; omit for a "
                        "harness+model with no dial")
    t.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.verb == "catalog":
            rows = catalog(args.profiles)
            print(json.dumps(rows, indent=2)) if args.json else _print_catalog(rows)
            return 0
        if args.verb == "inspect":
            out = inspect(args.workflow, args.config_root)
            if args.json:
                print(json.dumps(out, indent=2))
            else:
                print(f"{out['module']}/{out['component']} · workflow `{out['workflow']}` · "
                      f"code `{out['code']}`")
                print(f"manifest: {out['manifest']}")
                print(f"bindings: {out['bindings']}"
                      f"{'' if out['bindings-exists'] else '   (ABSENT — `scaffold` creates it)'}\n")
                for e in out["seats"]:
                    cast = e["cast"] or {}
                    state = (f"{cast.get('harness')}/{cast.get('model')}/{cast.get('effort')}"
                             if not e["uncast"] else "UNCAST")
                    print(f"  {e['seat']}\n      cast: {state}\n      def:  {e['definition']}")
                    if e.get("unresolved"):
                        print(f"      ⚠ {e['unresolved']}")
                    if e.get("staffing-hints"):
                        print(f"      hint: {e['staffing-hints']}  "
                              f"[{e['staffing-hints-source']}]")
                print(f"\nuncast: {', '.join(out['uncast']) if out['uncast'] else 'none'}")
                if out.get("warning"):
                    print(f"⚠ {out['warning']}")
            return 0
        if args.verb == "scaffold":
            print(json.dumps(scaffold(args.workflow, args.config_root, args.dry_run), indent=2))
            return 0
        out = set_seat(args.workflow, args.seat, args.harness, args.model, args.effort,
                       config_root=args.config_root, profiles_path=args.profiles,
                       dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        return 0
    except Refusal as exc:
        print(json.dumps({"ok": False, "refusal": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
