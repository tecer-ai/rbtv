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
  4. EVERY REFUSAL SHAPE LEAVES THE SHEET BYTE-IDENTICAL — unknown pair, effort out of range, effort
     on a dial-less pair, a seat the manifest does not carry, `set` before `scaffold`, and a second
     `scaffold`. Each refuses, each states why, and the file's sha256 is unchanged.
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
"""

import atexit
import hashlib
import importlib.util
import json
import os
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
    check("kimi and test-sleep are REPORTED not-castable with a stated reason, not dropped",
          all(any(r["profile"] == n and not r["castable"] and r["not-castable-because"]
                  for r in base) for n in ("kimi", "test-sleep")))
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
    check("scaffold filed the sheet at <root>/meta/planning/plan.json — the code is the manifest's "
          "shared seat prefix",
          sheet == croot / "meta" / "planning" / "plan.json", str(sheet))
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
    check("the sheet reports which seats remain uncast", len(r["uncast"]) == 15, str(len(r["uncast"])))

    before = sha(sheet)
    arms = [
        ("unknown pair (a model no profile pins)",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "probe-only-model", 4,
                              config_root=croot, profiles_path=LIVE_PROFILES)),
        ("effort out of range (6 on a five-rung ladder)",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "claude-opus-5", 6,
                              config_root=croot, profiles_path=LIVE_PROFILES)),
        ("effort on a dial-less pair (claude/claude-haiku-4-5 declares effort: inert)",
         lambda: mod.set_seat(LIVE_MANIFEST, "plan-planner", "claude", "claude-haiku-4-5", 2,
                              config_root=croot, profiles_path=LIVE_PROFILES)),
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
    check("a manifest with prefix `pxyz` files itself as pxyz.json under probemod/probecomp",
          Path(o["bindings"]) == croot / "probemod" / "probecomp" / "pxyz.json", o["bindings"])
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
     "    known[(harness, model)] = {'effort-levels': list(NATIVE_EFFORT.get(harness, ())),\n"
     "                               'effort-dial': None}\n",
     lambda m, mani, croot: m.set_seat(mani, "plan-planner", "claude", "probe-only-model", 4,
                                       config_root=croot, profiles_path=LIVE_PROFILES)),
    ("the native effort ladder's length", '"claude": ("low", "medium", "high", "xhigh", "max"),',
     '"claude": ("low", "medium", "high", "xhigh", "max", "probe-only-rung"),',
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
