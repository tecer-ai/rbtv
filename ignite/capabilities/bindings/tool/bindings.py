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

  1. WHICH harness+model pairs exist — `ignite/config/spawn-profiles.yaml` `launch-specs:`, which
     `#d-abolish-profile-names` KEYS BY THE PAIR ITSELF (2026-08-12) — `launch-specs: { <harness>:
     { <model>: … } }` — so the pairs are READ, not derived. That IS this workspace's spawnable
     set; a roster frozen in this file would admit a model the box cannot spawn or refuse one it
     can. The old derivation (harness = argv[0], model = the token after `--model`/`-m`) survives
     only as a config-LOAD guard on the daemon side (`profiles.js#validateSpecKey`), proving each
     spec's argv agrees with its key.
     ⚠ THE MODEL VOCABULARY IS THE SPEC'S KEY, VERBATIM — `claude-fable-5`, never `fable` (owner
     ruling 2026-08-10, which eliminated the earlier alias/full-id asymmetry in the config itself).
     The claude binary honours both an alias and a full model id (`claude --help`: "an alias … or a
     model's full name"), so BOTH forms would run; but only the keyed literal joins a bindings row
     back to a launch spec, and inventing the other form here would be a second mapping of the same
     fact — the drift DEC-1 § Shared launch-spec source exists to forbid. A caller passing an alias
     is REFUSED with the catalog's models printed, never silently rewritten.

  2. WHETHER a pair has an effort dial — the spec's own `effort:` block. `effort: { inert: true }`
     is a MEASUREMENT under G-270 ("a harness whose dial does not exist says so"), so an inert
     profile has NO dial — and a rung on it is ACCEPTED and stored as the word `inert`, never
     refused (owner ruling `d-effort-refuses-only-where-a-dial-exists`: refuse only where a dial
     EXISTS and the level is out of its range). ⚠ THIS REVERSED ON 2026-08-12. It refused until
     then, which made a `claude-haiku` cast un-makeable through this CLI — `cast_seat` popped the
     rung and `materialize-seats.py#open_binding` then refused the half-declared triple on a
     standing seat, so the channel master's own sheet had to be hand-written. A profile declaring
     no `effort:` block AT ALL still refuses a rung: there, nothing downstream could translate one.

  …and the LEVELS of a dial that exists come from THE SPEC'S OWN `effort.rungs` list — the one
  copy, read straight off `spawn-profiles.yaml` (`spec_effort` below, which is ALSO the
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
  set-many <workflow.csv> <casts.json>     cast N seats of ONE workflow in one validated call —
                                           ALL-OR-NOTHING: every seat is validated through the same
                                           `set` path first and the file is opened only if all pass

EVERY VERB ALSO TAKES A GOAL FOLDER in place of `<workflow.csv>` — the GOAL-LOCAL mode (owner
ruling 2026-08-14). Seats a planning pass authored inside the goal belong to no workflow, so the
canonical path above cannot name them; their sheet is `<goal>/planning/current/bindings.json`, read
by `ignite/engine/queue-request.js#buildGoalLocalSeats`, which refuses `goal-local-sheet-absent`
without it. Same verbs, same validator, same write — see `resolve_goal` below.

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


def spec_effort(harness, model, profiles_path=DEFAULT_PROFILES):
    """This (harness, model)'s ordered rungs. `[]` means an INERT dial; `None` means NO dial at all.

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
    block = ((doc.get("launch-specs") or {}).get(harness) or {}).get(model)
    effort = block.get("effort") if isinstance(block, dict) else None
    if not isinstance(effort, dict):
        return None                                 # no such spec, or a spec with no dial
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

# What the sheet stores as the effort of a cast onto an INERT profile (`effort: { inert: true }` —
# `claude-haiku`). It is not a rung name because that profile has no ladder to name one from; it is
# the honest word for what the seat's descriptor then carries, and every reader of that field
# already short-circuits on the profile's inert table before looking at the word. See `cast_seat`.
INERT_EFFORT = "inert"


class Refusal(Exception):
    """A refusal names what was rejected and what held instead — never a bare status."""


# ─────────────────────────────────────────────────────── the workflow → {module, component, code}

# ── THE GOAL-LOCAL SHEET (owner ruling 2026-08-14) ──────────────────────────────────────────────
#
# A planning pass can AUTHOR seats inside the goal itself — `planning/current/seats/<seat>/` holding
# the definition, not a `source.md` pointer at a cataloged one. Those seats belong to NO workflow, so
# the cataloged path above cannot name them: `bindings/<code>.json` is keyed by a workflow code they
# do not have (`ignite/engine/queue-request.js:390-399`). Their sheet therefore sits INSIDE the goal
# at `planning/current/bindings.json` — the path `buildGoalLocalSeats` reads and refuses
# `goal-local-sheet-absent` without (`queue-request.js:425-433`). Nothing wrote it until this mode
# existed, which is why the engine's own comment calls the cast of a goal-authored seat an open
# question. It is the SAME verbs, the SAME validator and the SAME write: only which seats exist, and
# where the file lands, change.
GOAL_LOCAL_SOURCE = ("planning", "current")
GOAL_LOCAL_SHEET = "bindings.json"
GOAL_LOCAL_REUSE = "source.md"          # "this seat is CATALOGED reuse" — not a goal-local seat


def resolve_goal(goal_folder):
    """`resolve_workflow`'s twin for a goal that authored its own seats — same keys, so every verb
    below is untouched. `sheet` is the one addition, and it is what makes `bindings_path` return
    the in-goal path instead of the deployment-config one.

    The seat set is the manifest's rows MINUS the cataloged reuses, which is exactly the set the
    materializer's `--goal-local` lane builds (`materialize-seats.py#build_goal_local_lane`) and
    therefore exactly the set `check_bindings_cover` demands the sheet's keys equal. Deriving it
    the same way is what makes an extra/missing key impossible to write here."""
    p = Path(goal_folder).resolve()
    src = p.joinpath(*GOAL_LOCAL_SOURCE)
    manifest = src / "manifest.csv"
    if not manifest.is_file():
        raise Refusal(f"{p} is a directory, so it is read as a GOAL folder — and it carries no "
                      f"{'/'.join(GOAL_LOCAL_SOURCE)}/manifest.csv. A goal-local casting sheet is "
                      f"authored against the goal's own planning product; a goal that ran no "
                      f"planning pass authored no seats. (For a CATALOGED workflow, name the "
                      f"manifest CSV itself, not a directory.)")
    seats = [s for s in manifest_seats(manifest)
             if (src / "seats" / s).is_dir()
             and not (src / "seats" / s / GOAL_LOCAL_REUSE).is_file()]
    if not seats:
        raise Refusal(f"{manifest} names no GOAL-LOCAL seat — every row is either a cataloged reuse "
                      f"(a `{GOAL_LOCAL_REUSE}` pointer) or has no definition folder at all. A "
                      f"cataloged seat is cast in its own workflow's sheet under "
                      f".rbtv/config/modules/…; this sheet would name seats the goal-local lane "
                      f"never materializes, which materialize refuses as `bindings-extra-seat`.")
    return {
        "manifest": manifest, "workspace": p, "module": "goal", "component": p.name,
        "component_dir": None, "catalog_root": src, "workflow": "goal-local",
        "seats": seats, "code": p.name, "sheet": src / GOAL_LOCAL_SHEET,
    }


def resolve_workflow(workflow_csv):
    """Everything the canonical path needs, derived from the manifest's own location.

    A mirrored workflow manifest sits at exactly
    `<ws>/.rbtv/mirror/<module>/<component>/workflows/<w>/<w>.csv` — the shape
    `materialize-seats` resolves through `<catalog-root>/<component>/workflows/…`. Anything else
    refuses: a path this function had to guess about would put the bindings file somewhere the next
    reader looks for in vain."""
    p = Path(workflow_csv).resolve()
    if p.is_dir():
        # A DIRECTORY is a goal folder, never a manifest — the goal-local mode, dispatched on the
        # argument's own shape rather than on a flag every verb would have to thread through.
        return resolve_goal(p)
    if not p.is_file():
        raise Refusal(f"{p} is not a file — name the workflow manifest CSV itself (or a GOAL "
                      f"folder, for the goal-local sheet)")
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
    if wf.get("sheet"):
        # GOAL-LOCAL: the sheet lives inside the goal because the seats do. No config root is
        # involved, and a caller passing one is refused rather than having it silently ignored.
        if config_root:
            raise Refusal(f"--config-root names where DEPLOYMENT config lives, and a goal-local "
                          f"casting sheet is not deployment config — it sits inside the goal, at "
                          f"{wf['sheet']}, because that is where `buildGoalLocalSeats` reads it.")
        return wf["sheet"]
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

def _launch_specs(profiles_path):
    """The `launch-specs:` block as {(harness, model): spec}.

    ⚠ THE KEYS ARE THE ANSWER — THERE IS NO DERIVATION LEFT HERE (owner ruling
    `#d-abolish-profile-names`, 2026-08-12). This used to be a LINE SCAN of a flat `profiles:` map
    plus `_exec_argv`, which re-derived each row's pair from its argv (`harness = basename(argv[0])`,
    `model = the token after --model/-m`) under a law spelled identically in
    `launch-profiles/catalog.js`. Re-keying the document by the pair deleted that law from both
    sides: the config STATES the pair, and the JS twin reads the same keys. What remains of the old
    derivation is a single LOAD-TIME GUARD on the daemon side (`profiles.js#validateSpecKey`),
    proving a spec's argv agrees with the key it is filed under — so this reader can trust the key
    without re-deriving it, and no drift between the two sides is expressible any more.

    A plain `yaml.safe_load`, and the old `ponytail:` line-scan ceiling (a non-standard indent or a
    quoted key was invisible) goes with it."""
    doc = yaml.safe_load(Path(profiles_path).read_text(encoding="utf-8")) or {}
    specs = doc.get("launch-specs")
    if not isinstance(specs, dict) or not specs:
        raise Refusal(f"{profiles_path} declares no root key `launch-specs:` — refusing to validate "
                      f"against a set this file does not carry. (It was `profiles:` before "
                      f"2026-08-12; `#d-abolish-profile-names` re-keyed it by (harness, model).)")
    out = {}
    for harness, models in specs.items():
        if not isinstance(models, dict):
            continue
        for model, spec in models.items():
            out[(str(harness), str(model))] = spec
    if not out:
        raise Refusal(f"the `launch-specs:` section of {profiles_path} declares no spec — refusing "
                      f"to validate against an empty set, which would refuse EVERY casting")
    return out


def catalog(profiles_path=DEFAULT_PROFILES):
    """Every harness+model this workspace can cast, with each one's effort numbers.

    THE ONE derivation: `catalog` prints it and `set` enforces it, so the surface an agent reads and
    the surface that refuses it are the same object."""
    validate_seat = _coord_validate_seat()
    rows = []
    for (harness, model), spec in _launch_specs(profiles_path).items():
        # ONE call answers both questions. The second `inert` regex that used to live here was a
        # third opinion on the same bytes, disagreeing with `spec_effort` by construction: it
        # could report a dial INERT while the levels beside it listed five rungs.
        levels = spec_effort(harness, model, profiles_path)
        reason = validate_seat({"agent": f"{harness}/{model}", "harness": harness, "model": model})
        rows.append({"spec": f"{harness}/{model}", "harness": harness, "model": model,
                     # `effort-levels` collapses the reader's three-way answer to a list, so the
                     # INERT case (`[]`) and the no-table-at-all case (`None`) read alike on it.
                     # They are not alike: a rung is ACCEPTED on the first and refused on the
                     # second (`cast_seat`), so the distinction gets its own key rather than a
                     # substring match on the prose below.
                     "effort-levels": list(levels or []), "effort-inert": levels == [],
                     "castable": not reason,
                     "not-castable-because": reason or None,
                     "effort-dial": "inert (the spec declares `effort: { inert: true }` — G-270: "
                                    "a harness whose dial does not exist says so)" if levels == []
                                    else ("none — this spec declares no effort ladder"
                                          if levels is None else None)})
    return rows


def castable(profiles_path=DEFAULT_PROFILES):
    """{(harness, model): row} — the enforced set."""
    return {(r["harness"], r["model"]): r for r in catalog(profiles_path) if r["castable"]}


def spec_row(harness, model, profiles_path=DEFAULT_PROFILES):
    """The catalog row a (harness, model) resolves to, or None.

    ⚠ IT REPLACES `profile_row(name)` (`#d-abolish-profile-names`, 2026-08-12). That function
    existed for ONE caller — the channel master's self-service knob, which held a profile NAME and
    needed the harness+model it stood for. The knob now takes harness and model directly, so the
    name-to-pair resolution it performed has no subject."""
    return next((r for r in catalog(profiles_path)
                 if r["harness"] == harness and r["model"] == model), None)


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
        if wf.get("sheet"):
            # GOAL-LOCAL: nothing catalogs these seats — the definition IS the goal's own seat
            # folder, and which .md inside it is the prompt half is the materializer's answer to
            # give (it keys on the `<role>`/`<task-goal>` section), never a second one from here.
            entry["definition"] = str(wf["catalog_root"] / "seats" / seat) + "/"
        elif not row:
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
    # ⚠ `ensure_ascii=False`, AND IT IS A FIX. Without it `json.dumps` escapes every non-ASCII
    # character, so writing ONE seat's cast also rewrote every line of prose in the sheet that
    # contained an em dash — `—` became `—` in the `_what`/`_code`/`description` keys nobody
    # touched. Measured 2026-08-12 on the channel master's sheet: a three-field change produced a
    # five-line prose diff. These files are hand-authored and read by humans; the two planning
    # sheets on this deployment already carry escaped dashes from earlier writes. The file is
    # opened as UTF-8 either way, so nothing about what parsers see changes.
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
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
        "_code": ((f"This is the GOAL-LOCAL sheet: it names the seats this goal's own planning pass "
                   f"authored, and it lives inside the goal because they do — a goal-authored seat "
                   f"belongs to no workflow, so no `bindings/<code>.json` can address it "
                   f"(queue-request.js:390-399). Cataloged reuses in the same manifest are cast in "
                   f"their own workflow's sheet and are deliberately absent here.")
                  if wf.get("sheet") else
                  (f"`{wf['code']}` is this workflow's CODE — the seat-id prefix every manifest row "
                   f"carries — and it is this file's name. Derived from the manifest, never typed.")),
        "defaults": dict(LANE_DEFAULTS),
        # `component` names the mirrored component home a cataloged seat's definitions come from; a
        # goal-authored seat has none (its definitions are the goal's own product), so the key is
        # ABSENT rather than pointed at the derived lane materialize rebuilds on every run.
        "seats": {seat: dict(LANE_PER_SEAT,
                             **{k: None for k in CASTING_KEYS},
                             **({"component": str(wf["component_dir"]) + "/"}
                                if wf["component_dir"] else {}))
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
    return cast_seat(path, seat, harness, model, effort_number, profiles_path, dry_run)


def cast_seat(path, seat, harness, model, effort_number,
              profiles_path=DEFAULT_PROFILES, dry_run=False):
    """Validate one cast against the catalog and write it into ONE seat of an EXISTING sheet.

    Split out of `set_seat` so a STANDING seat — whose sheet is named for the seat rather than
    derived from a workflow manifest, because a standing seat has no manifest (task 7.617) — casts
    through the SAME validator and the SAME write. `capabilities/master-profile` is that second
    caller: the channel master's own knob. Everything above this line is the WORKFLOW half —
    resolving which sheet and proving the seat is one of the manifest's; a caller that already
    knows its sheet and its seat has nothing to resolve and calls straight in here.
    """
    path = Path(path)
    if not path.is_file():
        raise Refusal(f"{path} does not exist. This writes one seat of an EXISTING sheet and never "
                      f"mints one, so a mistyped path cannot quietly create a casting sheet "
                      f"nobody reads.")

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
            + f"The set comes from `launch-specs:` in {profiles_path} — the model is the literal each "
              f"launch spec is FILED UNDER, and this tool never rewrites one spelling into another. "
              f"Run `catalog` to see every pair with its effort numbers.")

    levels = row["effort-levels"]
    inert = bool(row.get("effort-inert"))
    if inert:
        # OWNER RULING `d-effort-refuses-only-where-a-dial-exists` (2026-08-11): a cast refuses
        # ONLY where a dial EXISTS and the level is out of its range; where the model has NO dial
        # the declaration is ACCEPTED and reported inert (G-270), never dropped. This tool refused
        # instead until 2026-08-12 — the "known asymmetry" that ruling filed as defensible while
        # "nothing casts seats to either" inert profile. Something does: the channel master runs on
        # `claude-haiku` for the warm-session path, and the refusal made that cast UN-MAKEABLE
        # through the owner's own CLI (the rung was popped, then `materialize-seats.py#open_binding`
        # refused `open-binding-partial` on the standing seat, so the live sheet had to be
        # hand-written).
        #
        # THE STORED WORD IS `inert`, NOT A RUNG NAME, because there is no ladder to name one from.
        # It reads honestly in the seat's own descriptor and every downstream reader already agrees
        # with it: `profiles.js#resolveEffort` and `catalog.js#effortRungFor` report inert BEFORE
        # looking at the word, and `coord.py#validate_seat` validates a word only against a
        # non-empty ladder. An inert profile declares no range, so no rung is out of range on it and
        # a rung is accepted whether one is named or not.
        effort = INERT_EFFORT
    elif effort_number is None:
        if levels:
            raise Refusal(f"{harness}/{model} has an effort dial with {len(levels)} levels "
                          f"({', '.join(levels)}) — name one by number, 1..{len(levels)}. "
                          f"materialize refuses `effort-missing` on a seat with no effort.")
        effort = ""
    else:
        if not levels:
            raise Refusal(f"{harness}/{model} declares NO effort table at all "
                          f"({row['effort-dial']}), so effort number {effort_number} names nothing "
                          f"and nothing downstream could translate it — `resolveEffort` refuses a "
                          f"rung on such a profile too. A harness with no dial must declare "
                          f"`effort: {{ inert: true }}`, which IS accepted here and stored inert.")
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
            "effort-number": effort_number, "effort-ladder": levels, "effort-inert": inert,
            "uncast": uncast}


def read_casts(casts_json):
    """The batch input: {seat-id: {harness, model, effort?}} — or the SHEET's own `{"seats": {…}}`
    wrapper, which is what an author copying out of `inspect` or the file itself will hand you.

    Shape errors refuse HERE, before any seat is validated, because a malformed document has no
    per-seat reasons to give and printing "seat `seats` is not a seat" instead of "you handed me the
    wrapper" is the refusal that wastes the author's next ten minutes."""
    p = Path(casts_json)
    if not p.is_file():
        raise Refusal(f"{p} is not a file — `set-many` takes a JSON document of casts, one entry "
                      f"per seat: {{\"plan-binder\": {{\"harness\": \"claude\", \"model\": "
                      f"\"claude-opus-5\", \"effort\": 4}}, …}}")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Refusal(f"{p} is not valid JSON — {exc}")
    if isinstance(doc, dict) and isinstance(doc.get("seats"), dict):
        doc = doc["seats"]                              # the sheet's own shape, unwrapped
    if not isinstance(doc, dict) or not doc:
        raise Refusal(f"{p} must carry a non-empty object mapping seat-id → "
                      f"{{harness, model, effort}}; got {type(doc).__name__}")
    casts = {}
    for seat, spec in doc.items():
        if not isinstance(spec, dict):
            raise Refusal(f"{p}: seat `{seat}` maps to {type(spec).__name__}, not an object of "
                          f"{{harness, model, effort}}")
        missing = [k for k in ("harness", "model") if not spec.get(k)]
        unknown = sorted(set(spec) - set(CASTING_KEYS))
        if missing or unknown:
            raise Refusal(f"{p}: seat `{seat}` "
                          + (f"is missing {', '.join(missing)}. " if missing else "")
                          + (f"carries unknown key(s) {', '.join(unknown)}. " if unknown else "")
                          + f"An entry carries exactly harness, model and (where the pair has a "
                            f"dial) effort — the same three `set` takes.")
        effort = spec.get("effort")
        if effort is not None and not isinstance(effort, int):
            raise Refusal(f"{p}: seat `{seat}` gives effort {effort!r} — the effort is the 1-based "
                          f"NUMBER of a rung on that pair's ladder (see `catalog`), not its word. "
                          f"The FILE stores the word; the input is the number.")
        casts[seat] = (spec["harness"], spec["model"], effort)
    return casts


def set_many(workflow_csv, casts_json, config_root=None, profiles_path=DEFAULT_PROFILES,
             dry_run=False):
    """Cast N seats of ONE workflow in one call. ALL-OR-NOTHING, and refused WHOLE.

    ⚠ THE VALIDATION IS `set_seat` ITSELF, run `--dry-run` over every seat before any of them is
    written — not a second predicate that agrees with it. A batch verb whose accept/refuse rule was
    written twice would be the exact drift `catalog` exists to prevent one level down: the whole
    point of this capability is that what an agent is told it may cast and what is enforced are one
    object.

    The two passes are what "no half-applied cast" means: a batch with one bad seat leaves the sheet
    byte-identical and returns EVERY seat's reason, so the author fixes the document once instead of
    discovering the seats one refusal at a time. It exists because casting a whole workflow through
    the one-seat verb is N calls the caller must sequence, and an agent that gets seat 7 wrong has
    already half-cast a taskforce.

    ponytail: N dry-run passes then N real ones, each re-deriving the catalog off spawn-profiles.
    Ceiling: O(seats × profiles) YAML parses — milliseconds at this size. Upgrade path: hoist
    `castable()` if a workflow ever has hundreds of seats.
    """
    casts = read_casts(casts_json)
    refusals = {}
    for seat, (harness, model, effort) in casts.items():
        try:
            set_seat(workflow_csv, seat, harness, model, effort,
                     config_root=config_root, profiles_path=profiles_path, dry_run=True)
        except Refusal as exc:
            refusals[seat] = str(exc)
    if refusals:
        # Grouped by REASON, not listed per seat: `set-many` before `scaffold` refuses every seat
        # for the same paragraph, and N copies of it buries the one sentence the author needs.
        by_reason = {}
        for seat, why in refusals.items():
            by_reason.setdefault(why, []).append(seat)
        raise Refusal(
            f"{len(refusals)} of {len(casts)} seat(s) in {casts_json} could not be cast, so NONE "
            f"were written — the sheet is untouched. Fix the document and run once more:\n"
            + "\n".join(f"  · {', '.join(seats)}: {why}" for why, seats in by_reason.items()))
    applied = [set_seat(workflow_csv, seat, harness, model, effort,
                        config_root=config_root, profiles_path=profiles_path, dry_run=dry_run)
               for seat, (harness, model, effort) in casts.items()]
    return {"ok": True, "action": "set-many" if not dry_run else "dry-run",
            "bindings": applied[-1]["bindings"], "casts": len(applied),
            "seats": {r["seat"]: r["after"] for r in applied},
            # …minus this batch's own seats: under --dry-run nothing was written, so the last call's
            # list still names every seat this batch just cast.
            "uncast": [s for s in applied[-1]["uncast"] if s not in casts]}


# ─────────────────────────────────────────────────────────────────────── cli

def _print_catalog(rows):
    print("harness+model this workspace can cast — from `launch-specs:` in spawn-profiles.yaml, "
          "gated by coord.py#validate_seat\n")
    w = max(len(f"{r['harness']}/{r['model']}") for r in rows)
    for r in sorted(rows, key=lambda r: (not r["castable"], r["harness"], r["model"])):
        pair = f"{r['harness']}/{r['model']}".ljust(w)
        if not r["castable"]:
            print(f"  --  {pair}  NOT CASTABLE — {r['not-castable-because']}")
            continue
        dial = ("  ".join(f"{i}={lv}" for i, lv in enumerate(r["effort-levels"], 1))
                if r["effort-levels"] else f"no effort dial — {r['effort-dial']}")
        print(f"  ok  {pair}  {dial}")
    print("\nthe effort NUMBER is the index; the file stores the harness's own level string")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="rbtv-bindings",
        description="author the casting sheet that turns a workflow into a taskforce — the "
                    "per-seat harness/model/effort file materialize-seats.py reads as --bindings. "
                    "Every verb's <workflow> may instead be a GOAL FOLDER: the goal-local sheet at "
                    "<goal>/planning/current/bindings.json, for seats the goal's own planning pass "
                    "authored (they belong to no workflow, so no bindings/<code>.json names them)")
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

    m = sub.add_parser("set-many", parents=[root, prof],
                       help="cast N seats of one workflow from a JSON file, all-or-nothing")
    m.add_argument("workflow")
    m.add_argument("casts", help='JSON: {"<seat>": {"harness": …, "model": …, "effort": <number>}, '
                                 '…} — the sheet\'s own {"seats": {…}} wrapper is accepted too')
    m.add_argument("--dry-run", action="store_true")

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
        if args.verb == "set-many":
            print(json.dumps(set_many(args.workflow, args.casts, config_root=args.config_root,
                                      profiles_path=args.profiles, dry_run=args.dry_run), indent=2))
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
