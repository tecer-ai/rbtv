#!/usr/bin/env python3
"""probe-bindings.py — the casting-sheet tool, proven against copies.

NOTHING HERE TOUCHES THE LIVE BINDINGS TREE OR THE LIVE MIRROR. Every write lands under `tempfile`:
the catalog is derived from a byte-copy of `ignite/config/spawn-profiles.yaml`, the casting sheets
are written under a throwaway `--config-root`, and the one materialize exercise runs into a
throwaway goal package with `--dry-run`. The live `.rbtv/config/modules/` is read by nothing here.

  1. THE CATALOG IS DERIVED, NOT REMEMBERED — re-pin a model in a COPY of spawn-profiles and the
     catalog follows it; delete a profile and it leaves. A catalog that answered from a frozen
     roster would pass a check that only asked "is opus there?".
  2. EVERY CATALOG ROW SURVIVES THE GATE MATERIALIZE APPLIES — each castable pair is re-run through
     `coord.py#validate_seat`, the same predicate `materialize-seats.py`'s F6 gate imports. A pair
     this tool offers and materialize then refuses is the one failure that would reach a real goal
     creation. `kimi` and `test-sleep` must be REPORTED not-castable, not silently dropped.
  3. THE EFFORT NUMBER IS AN INDEX INTO THE NATIVE LADDER, AND THE FILE STORES THE STRING — `set …
     4` on claude writes `xhigh`, read back FROM THE FILE. `xhigh` is exactly the rung the profile's
     four-level translation table does not carry, so this check also discriminates "native ladder"
     from "profile table".
  3b. AN INERT DIAL ACCEPTS THE RUNG AND STORES `inert` — `claude/claude-haiku-4-5`, with a rung and
     without one (owner ruling `d-effort-refuses-only-where-a-dial-exists`). This tool REFUSED it
     until 2026-08-12, popping the field, after which `open_binding` refused the half-declared
     triple on the standing channel-master seat: the master's live cast was un-makeable through the
     CLI. Reds if that refusal returns.
  4. EVERY REFUSAL SHAPE LEAVES THE SHEET BYTE-IDENTICAL — unknown pair, effort out of range, a rung
     on a profile declaring NO effort table at all (the ruling's other half, run against a COPY of
     the profiles document with haiku's table deleted, since no live profile is in that state), a
     seat the manifest does not carry, `set` before `scaffold`, and a second `scaffold`. Each
     refuses, each states why, and the file's sha256 is unchanged.
  5. THE CODE IS DERIVED FROM THE MANIFEST — a manifest whose rows share no prefix REFUSES rather
     than picking one, and the filename follows the prefix when it changes.
  6. THE MUTANTS — four, each re-running one arm of check 4/5 against a source copy with exactly one
     guard WIDENED (never deleted: a deletion crashes on the value the guard protected, and a crash
     reads the same as a refusal). Each MUST flip to accepted. An arm that stays refused is scoring
     nothing — it would pass against a validator that refused everything — and this probe then exits
     2 INOPERATIVE rather than reporting a pass it did not earn.
  7. MATERIALIZE ACCEPTS THE PRODUCT — a sheet this tool scaffolded and cast is handed to
     `materialize-seats.py --dry-run` over the real `planning` manifest and a throwaway package.
     Every other check exercises this tool alone; this one is the only evidence that the artifact it
     writes is the artifact the consumer reads. Its negative twin: the SAME call with one seat left
     uncast must refuse.
  8. THE BOTH-DOORS SWEEP — every rung of every CASTABLE ladder is composed twice, by the daemon
     door (`launch-profiles/profiles.js#resolveEffort`, loaded through the daemon's own
     `server/spawn/config.js`) and by the tmux door (`team-kit/coord.py#harness_command`), and the
     two must yield the same tokens in the same order. Its COVERAGE FLOOR is the check, not its
     setup: the sweep refuses to grade until it has seen more than one harness and more than one
     dialect, because every live seat is claude and a claude-only matrix would pass every cell
     while certifying the exact defect this closes. That floor is proven to FIRE by handing the
     same predicate a claude-only cell set. One `node` call covers the whole matrix — a scheduled
     probe cannot afford a process per cell.
"""

import atexit
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tool" / "bindings.py"
IGNITE = Path(__file__).resolve().parents[3]
LIVE_PROFILES = IGNITE / "config" / "spawn-profiles.yaml"
MATERIALIZE = IGNITE / "team-kit" / "materialize-seats.py"
STARTER = IGNITE / "team-kit" / "starter-set"
WORKSPACE = IGNITE.parents[3]
LIVE_MANIFEST = (WORKSPACE / ".rbtv" / "mirror" / "meta" / "planning"
                 / "workflows" / "planning" / "planning.csv")

failures: list[str] = []
inoperative: list[str] = []


# The adjacent `.out` capture, written whatever happens — the suite grades a probe STALE when its
# capture was not written inside the run's own window, so the write must survive a crash too.
class _Tee:
    def __init__(self, real):
        self.real, self.buf = real, []

    def write(self, s):
        self.real.write(s)
        self.buf.append(s)
        return len(s)

    def flush(self):
        self.real.flush()


_tee = _Tee(sys.stdout)
sys.stdout = _tee
atexit.register(lambda: Path(__file__).with_suffix(".out").write_text("".join(_tee.buf),
                                                                     encoding="utf-8"))



def load(path=TOOL, name="bindings_mod"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)
    return ok


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def refuses(fn, *a, **kw):
    """(refused?, message). A refusal must be the tool's own typed one, never an incidental crash."""
    mod = kw.pop("_mod")
    try:
        fn(*a, **kw)
        return False, "ACCEPTED"
    except mod.Refusal as exc:
        return True, str(exc)


mod = load()

# ─────────────────────────────────────────────────────────────────────────────── check 1 + 2
print("check 1/2 — the catalog is derived from the profiles document and survives validate_seat")
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    copy = td / "spawn-profiles.yaml"
    shutil.copy2(LIVE_PROFILES, copy)
    base = mod.catalog(copy)
    pairs = {(r["harness"], r["model"]) for r in base}
    check("the live-copy catalog carries claude/claude-fable-5 and claude/claude-opus-5 — the FULL "
          "model ids the shipped profiles pin (no aliases, owner ruling 2026-08-10)",
          ("claude", "claude-fable-5") in pairs and ("claude", "claude-opus-5") in pairs,
          f"{len(base)} rows")
    check("test-sleep is REPORTED not-castable with a stated reason, not dropped — its `exec:` argv "
          "is `sleep`, a harness no launch door speaks",
          any(r["profile"] == "test-sleep" and not r["castable"] and r["not-castable-because"]
              for r in base))
    check("kimi is CASTABLE — it was reported not-castable only because `coord.py#HARNESSES` did "
          "not carry it, so `validate_seat` refused `unknown harness` before its fully authored "
          "profile was ever reached. This row moves with that predicate, which is the whole reason "
          "the catalog is gated on it rather than on a list kept here",
          any(r["profile"] == "kimi" and r["castable"] for r in base))
    vs = mod._coord_validate_seat()
    bad = [f"{r['harness']}/{r['model']}" for r in base if r["castable"]
           and vs({"agent": r["profile"], "harness": r["harness"], "model": r["model"]})]
    check("every castable pair passes coord.py#validate_seat — the predicate materialize's F6 gate "
          "imports", not bad, f"offenders: {bad}")

    # THE DERIVATION ARM: re-pin a model in the copy; the catalog must move with it.
    text = copy.read_text(encoding="utf-8")
    copy.write_text(text.replace('"--model", "claude-opus-5"', '"--model", "probe-only-model"'),
                    encoding="utf-8")
    moved = {(r["harness"], r["model"]) for r in mod.catalog(copy)}
    check("re-pinning a profile's --model in the copy MOVES the catalog — it is read, not "
          "remembered",
          ("claude", "probe-only-model") in moved and ("claude", "claude-opus-5") not in moved)
    copy.write_text(text, encoding="utf-8")

# ─────────────────────────────────────────────────────────────────── checks 3 + 4 + 5
print("check 3/4/5 — scaffold + set land, every refusal shape leaves the sheet byte-identical, "
      "and the code is derived")
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    croot = td / "bindings"
    out = mod.scaffold(LIVE_MANIFEST, croot)
    sheet = Path(out["bindings"])
    check("scaffold filed the sheet at the D15 module-first path "
          "<root>/modules/meta/planning/bindings/plan.json — the code is the manifest's shared "
          "seat prefix",
          sheet == croot / "modules" / "meta" / "planning" / "bindings" / "plan.json", str(sheet))
    doc = json.loads(sheet.read_text())
    manifest_seats = mod.manifest_seats(LIVE_MANIFEST)
    check("every manifest seat is present and UNCAST",
          set(doc["seats"]) == set(manifest_seats)
          and all(doc["seats"][s]["harness"] is None for s in manifest_seats),
          f"{len(doc['seats'])} seats")
    check("the lane constants are prefilled so a cast sheet is materializable",
          doc["defaults"] == {"cwd-mode": "seat-folder"}
          and doc["seats"]["plan-binder"]["mode"] == "interactive"
          and doc["seats"]["plan-binder"]["agent_type"] == "staff"
          and doc["seats"]["plan-binder"]["ctx-refresh"] == 35)

    r = mod.set_seat(LIVE_MANIFEST, "plan-binder", "claude", "claude-opus-5", 4,
                     config_root=croot, profiles_path=LIVE_PROFILES)
    stored = json.loads(sheet.read_text())["seats"]["plan-binder"]
    check("effort NUMBER 4 stored as the native STRING `xhigh`, read back from the FILE — the rung "
          "the profile's four-level translation table does not carry",
          stored["effort"] == "xhigh" and stored["model"] == "claude-opus-5", json.dumps(stored))
    check("the sheet reports which seats remain uncast — every manifest seat but the one just cast",
          len(r["uncast"]) == len(manifest_seats) - 1,
          f"{len(r['uncast'])} of {len(manifest_seats)}")

    # AN INERT DIAL ACCEPTS A RUNG AND STORES THE WORD `inert` — owner ruling
    # `d-effort-refuses-only-where-a-dial-exists` ("refuse only where a dial EXISTS and the level is
    # out of its range"). ⚠ THIS IS THE REGRESSION GUARD FOR A MEASURED DEFECT, not a style check:
    # this tool REFUSED the rung until 2026-08-12 and POPPED the field with it, after which
    # `materialize-seats.py#open_binding` refused the half-declared triple on the STANDING
    # channel-master seat — so the master's live `claude-haiku` cast could not be made through the
    # owner's own CLI at all and its sheet had to be hand-written. Both arms are asserted, rung
    # named and rung omitted, because the omitted one is the half that produced the partial triple.
    # The Refusal is CAUGHT rather than left to propagate: a regression here is the old refusal
    # coming back, and an uncaught one would kill the probe mid-file — red either way, but with no
    # named check and no capture written. Caught, the regression reports itself in one line.
    ir, with_rung, no_rung, stated = None, {}, {}, ""
    try:
        ir = mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "claude-haiku-4-5", 2,
                          config_root=croot, profiles_path=LIVE_PROFILES)
        with_rung = json.loads(sheet.read_text())["seats"]["plan-planner"]
        mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "claude-haiku-4-5", None,
                     config_root=croot, profiles_path=LIVE_PROFILES)
        no_rung = json.loads(sheet.read_text())["seats"]["plan-planner"]
    except mod.Refusal as exc:
        stated = f"REFUSED: {exc}"
    check("a rung on an INERT profile (claude/claude-haiku-4-5) is ACCEPTED and stored as the word "
          "`inert` — with a rung AND without one, so the triple is never half-declared",
          with_rung.get("effort") == "inert" and no_rung.get("effort") == "inert"
          and (ir or {}).get("effort-inert") is True,
          stated[:200] or (f"with rung {with_rung.get('effort')!r}, without "
                           f"{no_rung.get('effort')!r}, effort-inert={ir['effort-inert']!r}"))

    # …and the OTHER half of the same ruling still refuses: a profile declaring NO `effort:` block
    # at all cannot translate a rung, and neither can anything downstream (`resolveEffort` throws
    # E_UNKNOWN_EFFORT on it). No LIVE profile is in that state — `loadConfig` forces a dial-less
    # harness to say `inert: true` — so the arm runs against a COPY with haiku's one-line table
    # deleted, and the deletion is asserted to have landed rather than assumed.
    no_dial = td / "no-dial-profiles.yaml"
    no_dial.write_text(LIVE_PROFILES.read_text(encoding="utf-8")
                       .replace("    effort: { inert: true }\n", "", 1), encoding="utf-8")
    if mod.profile_effort("claude-haiku", no_dial) is not None:
        inoperative.append("the no-effort-table fixture still declares a dial — its arm scores nothing")

    before = sha(sheet)
    arms = [
        ("unknown pair (a model no profile pins)",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "probe-only-model", 4,
                              config_root=croot, profiles_path=LIVE_PROFILES)),
        ("effort out of range (6 on a five-rung ladder)",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "claude-opus-5", 6,
                              config_root=croot, profiles_path=LIVE_PROFILES)),
        ("effort on a pair whose profile declares NO effort table at all",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "claude-haiku-4-5", 2,
                              config_root=croot, profiles_path=no_dial)),
        ("a seat the manifest does not carry",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-nonesuch", "claude", "claude-opus-5", 4,
                              config_root=croot, profiles_path=LIVE_PROFILES)),
        ("a second scaffold over an existing sheet",
         lambda: mod.scaffold(LIVE_MANIFEST, croot)),
    ]
    for label, fn in arms:
        refused, msg = refuses(fn, _mod=mod)
        check(f"{label}: refused, sheet byte-identical, and the author can read why",
              refused and sha(sheet) == before, msg[:150])

    refused, msg = refuses(lambda: mod.set_seat(LIVE_MANIFEST, "plan-binder", "claude", "claude-opus-5", 4,
                                                config_root=td / "empty",
                                                profiles_path=LIVE_PROFILES), _mod=mod)
    check("`set` before `scaffold`: refused rather than minting a second sheet nobody reads",
          refused, msg[:120])

    # check 5 — the code derivation itself, on a fabricated manifest
    fake = td / "mirror" / "probemod" / "probecomp" / "workflows" / "probe" / "probe.csv"
    fake.parent.mkdir(parents=True)
    fake.write_text("Seat/workflow,after\npxyz-one,\npxyz-two,pxyz-one\n", encoding="utf-8")
    o = mod.scaffold(fake, croot)
    check("a manifest with prefix `pxyz` files itself as pxyz.json under the D15 path "
          "modules/probemod/probecomp/bindings",
          Path(o["bindings"]) == croot / "modules" / "probemod" / "probecomp" / "bindings"
          / "pxyz.json", o["bindings"])
    fake.write_text("Seat/workflow,after\npxyz-one,\nabcd-two,pxyz-one\n", encoding="utf-8")
    refused, msg = refuses(lambda: mod.scaffold(fake, croot), _mod=mod)
    check("a manifest whose rows share NO prefix refuses rather than picking one", refused, msg[:120])

    # The FOUR-LETTER rule (owner ruling 2026-08-10). The prefix is shared and non-empty on every
    # arm below, so length/alphabet is the only thing under test.
    for label, seats in (("five letters", "plans-one,\nplans-two,plans-one"),
                         ("three letters", "pla-one,\npla-two,pla-one"),
                         ("four with a digit", "pl4n-one,\npl4n-two,pl4n-one")):
        fake.write_text(f"Seat/workflow,after\n{seats}\n", encoding="utf-8")
        refused, msg = refuses(lambda: mod.scaffold(fake, croot), _mod=mod)
        check(f"a workflow code of {label} is REFUSED — exactly four ASCII letters, named in the "
              f"refusal", refused and "four ASCII letters" in msg, msg[:150])
    fake.write_text("Seat/workflow,after\nplan-one,\nplan-two,plan-one\n", encoding="utf-8")
    o = mod.scaffold(fake, croot)
    check("...and a four-letter code still files normally, so the guard is not a blanket refusal",
          Path(o["bindings"]).name == "plan.json", o["bindings"])

# ────────────────────────────────────────────────────────────────────────────────── check 6
print("check 6 — the mutants: widen one guard each and the matching arm MUST flip to accepted")
# Each mutant WIDENS the guard rather than deleting it. A deletion crashes downstream on the value
# the guard was protecting, and a crash is indistinguishable from a refusal — the arm would score
# nothing either way, which is the very thing these mutants exist to disprove.
def _five_letter_arm(m, croot):
    """Scaffold from a manifest whose shared prefix is FIVE letters. Under the guard this refuses;
    with the length check widened it goes through — which is what makes the arm above a check."""
    fake = croot.parent / "mirror" / "probemod" / "probecomp" / "workflows" / "wide" / "wide.csv"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text("Seat/workflow,after\nplans-one,\nplans-two,plans-one\n", encoding="utf-8")
    return m.scaffold(fake, croot)


MUTANTS = [
    ("the four-letter workflow-code rule", "    if len(code) != 4 or not code.isascii()",
     "    if len(code) not in (4, 5) or not code.isascii()",
     lambda m, mani, croot: _five_letter_arm(m, croot)),
    ("the castable-pair set", "    known = castable(profiles_path)\n",
     "    known = dict(castable(profiles_path))\n"
     "    known[(harness, model)] = {'effort-levels': ['low', 'medium', 'high', 'xhigh', 'max'],\n"
     "                               'effort-dial': None}\n",
     lambda m, mani, croot: m.set_seat(mani, "plan-planner", "claude", "probe-only-model", 4,
                                       config_root=croot, profiles_path=LIVE_PROFILES)),
    # Retargeted 2026-08-11: the per-harness `NATIVE_EFFORT` table this used to mutate is DELETED
    # (effort is per MODEL, owner-ruled), and the ladder is now read off each profile's own
    # `rungs:` list. The equivalent mutation is therefore in the READER — widen every profile's
    # ladder by one and the out-of-range rung 6 becomes acceptable, which is the same discrimination
    # the old mutant proved against the old source.
    # Retargeted AGAIN 2026-08-11 (same day): the reader is no longer the `_profile_rungs` text
    # scrape — it is `profile_effort`, a `yaml.safe_load` parse shared with the master-profile
    # capability. The anchor moved with it; the arm and its discrimination are unchanged. ⚠ AN
    # ANCHOR THAT ROTS DOES NOT GO QUIET: it reported INOPERATIVE + FAIL here the moment the line
    # left the source, which is how this retarget was found rather than assumed.
    ("the profile ladder reader's length",
     "    return [str(r) for r in rungs] if isinstance(rungs, list) and rungs else None",
     '    return [str(r) for r in rungs] + ["probe-only-rung"] if isinstance(rungs, list) and rungs else None',
     lambda m, mani, croot: m.set_seat(mani, "plan-planner", "claude", "claude-opus-5", 6,
                                       config_root=croot, profiles_path=LIVE_PROFILES)),
    ("the manifest-membership check", 'if seat not in wf["seats"]:', "if False:",
     lambda m, mani, croot: m.set_seat(mani, "plan-nonesuch", "claude", "claude-opus-5", 4,
                                       config_root=croot, profiles_path=LIVE_PROFILES)),
]
src = TOOL.read_text(encoding="utf-8")
for i, (label, needle, replacement, arm) in enumerate(MUTANTS):
    if src.count(needle) != 1:
        inoperative.append(f"mutant '{label}': the mutation target is not uniquely locatable")
        check(f"mutant — {label}", False, "the mutation target is not uniquely locatable in the source")
        continue
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # The mutant is planted four levels deep because the module resolves its own repo roots
        # from `__file__` at import; the two roots are then repointed at the live ones, so the
        # ONLY difference between mutant and control is the removed guard.
        mpath = td / "capabilities" / "bindings" / "tool" / f"mutant_{i}.py"
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(src.replace(needle, replacement), encoding="utf-8")
        mut = load(mpath, f"bindings_mutant_{i}")
        mut.TEAM_KIT, mut.DEFAULT_PROFILES = mod.TEAM_KIT, mod.DEFAULT_PROFILES
        croot = td / "bindings"
        mut.scaffold(LIVE_MANIFEST, croot)
        try:
            arm(mut, LIVE_MANIFEST, croot)
            accepted, why = True, ""
        except Exception as exc:
            accepted, why = False, f"{type(exc).__name__}: {exc}"
        if not accepted:
            inoperative.append(f"mutant '{label}' stayed refused — its arm scores nothing")
        check(f"mutant — {label} widened: the arm is now ACCEPTED, so the check discriminates",
              accepted, why[:150])

# ────────────────────────────────────────────────────────────────────────────────── check 7
print("check 7 — materialize-seats reads the product: a fully cast sheet plans, a partly cast one "
      "refuses")
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    croot = td / "bindings"
    # `validate_package` accepts any absolute path whose PARENT is named `goals` — a throwaway one
    # under tempfile keeps the live goals tree out of this entirely.
    pkg = td / "goals" / "probe-bindings"
    pkg.mkdir(parents=True)   # materialize COMPLETES an existing goal folder; creating one is rbtv-goal's act
    out = mod.scaffold(LIVE_MANIFEST, croot)
    sheet = Path(out["bindings"])
    seats = mod.manifest_seats(LIVE_MANIFEST)
    for seat in seats[:-1]:
        mod.set_seat(LIVE_MANIFEST, seat, "claude", "claude-opus-5", 4,
                     config_root=croot, profiles_path=LIVE_PROFILES)

    def materialize():
        return subprocess.run(
            [sys.executable, str(MATERIALIZE),
             "--package", str(pkg), "--workflow", "planning",
             "--catalog-root", str(WORKSPACE / ".rbtv" / "mirror" / "meta"),
             "--root", "--bindings", str(sheet),
             "--conduct", str(STARTER / "conduct.md"),
             "--claude-md", str(STARTER / "CLAUDE.md"),
             "--budget-json", str(STARTER / "budget.json"),
             "--dry-run"], capture_output=True, text=True)

    r = materialize()
    out = r.stdout + r.stderr
    check("the NEGATIVE twin: one seat left uncast and materialize REFUSES the WHOLE batch rather "
          "than defaulting a binding",
          r.returncode != 0 and "model-invalid" in out,
          out.strip().splitlines()[-1][:160] if out.strip() else f"exit {r.returncode}")

    mod.set_seat(LIVE_MANIFEST, seats[-1], "claude", "claude-opus-5", 4,
                 config_root=croot, profiles_path=LIVE_PROFILES)
    r = materialize()
    check("a fully cast sheet plans clean under --dry-run (exit 0)", r.returncode == 0,
          (r.stderr or r.stdout).strip()[-200:] if r.returncode else "")
    # Counted off the write plan, not off a returned summary: the plan names the FILES it would
    # write, which is the thing the consumer would actually produce.
    check("the write plan carries one seat descriptor per manifest seat",
          r.stdout.count("seat-descriptor:") == len(seats),
          f"{r.stdout.count('seat-descriptor:')} of {len(seats)}")
    check("--dry-run wrote nothing into the package", not any(pkg.iterdir()))

# ────────────────────────────────────────────────────────────────────────────────── check 8
#
# THE BOTH-DOORS SWEEP. A seat's declared effort reaches a binary through two independent
# compositions: the DAEMON door (`launch-profiles/profiles.js#resolveEffort`, reached here through
# `server/spawn/config.js` so the loader is the daemon's own) and the TMUX door
# (`team-kit/coord.py#harness_command`). Until 2026-08-11 the second one hardcoded claude's
# `--effort {word}` and nothing else, so a codex seat (a real 3-rung ladder), a kimi seat and all
# seven opencode seats launched with their declared effort SILENTLY DROPPED — and an invalid
# opencode `--variant` exits 0 applying nothing, so even the binary would not have said so.
#
# ⚠⚠ THE COVERAGE ASSERTION IS THE POINT OF THIS CHECK, NOT ITS PREAMBLE. Every one of the 21 live
# seats is claude, and the selftest arm that asserts the claude case passed throughout the entire
# life of the defect. A matrix that silently collapsed to claude-only would therefore pass every
# cell it compared AND certify exactly the bug — so the sweep refuses to grade itself until it has
# seen MORE THAN ONE HARNESS and MORE THAN ONE DIALECT. The floor is proven to FIRE below, by
# handing the same predicate a single-profile cell set.
print("check 8 — the BOTH-DOORS sweep: daemon and tmux spell every rung of every castable ladder "
      "identically")

# ONE node call for the WHOLE matrix. Per-cell subprocesses would make a scheduled probe unusably
# slow (~40 node boots), and the daemon side is a pure function of the config — there is nothing a
# per-cell process could observe that this cannot.
_DOOR_A = r"""
const cfgmod = require(process.argv[1]);
const cfg = cfgmod.loadConfig(process.argv[2]);
const out = [];
for (const [name, p] of Object.entries(cfg.profiles || {})) {
  const eff = p && p.effort;
  if (!eff || eff.inert === true || !Array.isArray(eff.rungs)) continue;
  for (let r = 1; r <= eff.rungs.length; r += 1) {
    const res = cfgmod.resolveEffort(p, r, name);
    out.push({ profile: name, rung: r, word: eff.rungs[r - 1], argv: res.argv,
               dialect: (res.applied || {}).dialect });
  }
}
process.stdout.write(JSON.stringify(out));
"""

sys.path.insert(0, str(IGNITE / "team-kit"))
import coord as coord_mod  # noqa: E402 — the tmux door itself, never a re-implementation of it

_r = subprocess.run(["node", "-e", _DOOR_A, str(IGNITE / "server" / "spawn" / "config.js"),
                     str(LIVE_PROFILES)], capture_output=True, text=True)
if _r.returncode != 0:
    inoperative.append("door A did not run — the whole sweep scored nothing")
    check("door A (the daemon's own loader + resolveEffort) answers for the live profiles",
          False, (_r.stderr or _r.stdout).strip().splitlines()[-1][:180] if (_r.stderr or _r.stdout)
          else f"exit {_r.returncode}")
    cells = []
else:
    _castable = mod.castable(LIVE_PROFILES)                    # {(harness, model): row}
    _by_profile = {row["profile"]: (h, m) for (h, m), row in _castable.items()}
    # A cell is (harness, model, rung word, door-A argv, dialect). Profiles with a ladder this
    # workspace cannot CAST are skipped: a pair `harness_command` would refuse is not a
    # disagreement between the doors, it is a pair with no second door.
    cells = [(_by_profile[c["profile"]][0], _by_profile[c["profile"]][1],
              c["word"], [str(a) for a in c["argv"]], c["dialect"])
             for c in json.loads(_r.stdout) if c["profile"] in _by_profile]


def _coverage(cs):
    """(harnesses, dialects) a cell set exercises — the sweep's own floor, and its own mutant."""
    return {c[0] for c in cs}, {c[4] for c in cs}


_h, _d = _coverage(cells)
_covered = check(
    "COVERAGE FLOOR — the sweep exercised more than one harness AND more than one dialect before "
    "comparing anything. Every live seat is claude and the claude case already passed for the "
    "whole life of the defect, so a matrix that collapsed to claude-only would certify the bug "
    "with a full green sweep",
    len(_h) > 1 and len(_d) > 1,
    f"{len(cells)} cells · harnesses {sorted(_h)} · dialects {sorted(_d)}")

if not _covered:
    inoperative.append("the sweep's coverage floor was not met — its cells scored nothing")
else:
    _mismatch = []
    for harness, model, word, argv_a, _dialect in cells:
        seat = {"agent": "sweep", "harness": harness, "model": model, "effort": word,
                "cwd": "/tmp"}
        cmd_b, err_b = coord_mod.harness_command(seat, prompt_path="/tmp/p.txt")
        toks = shlex.split(cmd_b) if cmd_b else []
        # A CONTIGUOUS token subsequence, so this scores the flag SPELLING and the literal and
        # their ORDER — `--variant max` passing because `max` appears somewhere in the line would
        # be the check grading itself.
        if not any(toks[i:i + len(argv_a)] == argv_a for i in range(len(toks) + 1)):
            _mismatch.append(f"{harness}/{model} rung '{word}': door A {argv_a} absent from "
                             f"door B {cmd_b or ('REFUSED: ' + err_b)}")
        if coord_mod.validate_seat(seat):
            _mismatch.append(f"{harness}/{model} rung '{word}': on its OWN profile's ladder yet "
                             f"validate_seat refuses it — {coord_mod.validate_seat(seat)}")
    check("every rung of every castable ladder reaches BOTH doors as the same tokens, in the same "
          "order — and each is accepted by the launch predicate that gates the tmux door",
          not _mismatch, "; ".join(_mismatch[:3]) or f"{len(cells)} cells agree")

    # THE FLOOR'S OWN MUTANT: the identical predicate over a single-harness cell set MUST fail.
    # Without this the floor is a sentence, not a check — it would read as satisfied whether or not
    # it could ever have said no.
    _one = [c for c in cells if c[0] == "claude"]
    _h1, _d1 = _coverage(_one)
    check("the coverage floor FIRES: handed a single-profile-family cell set (claude only, the "
          "exact shape the defect survived under) the SAME predicate reports insufficient — so the "
          "green above is a floor that was cleared, not one that cannot fail",
          bool(_one) and not (len(_h1) > 1 and len(_d1) > 1),
          f"{len(_one)} claude cells · harnesses {sorted(_h1)} · dialects {sorted(_d1)}")

verdict = ("INOPERATIVE" if inoperative else ("FAIL" if failures else "PASS"))
print(f"probe-bindings: {verdict} — "
      + ("; ".join(inoperative) if inoperative else
         ("; ".join(failures) if failures else
          "the catalog is derived from the live profiles document and every pair it offers passes "
          "the gate materialize applies, the effort number indexes the harness's NATIVE ladder "
          "while the file stores the string, every refusal shape leaves the sheet byte-identical "
          "and four of them are proven discriminating by mutation, and materialize-seats plans "
          "clean over the artifact this tool writes")))
sys.exit(2 if inoperative else (1 if failures else 0))
