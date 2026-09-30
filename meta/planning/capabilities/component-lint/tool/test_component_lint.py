#!/usr/bin/env python3
"""Assert-based self-test for component_lint.py. No external framework.

EVERY check ships a RED ARM: a fixture mutation that makes exactly that check
fail for exactly the right reason. A check never observed failing is not
evidence. The green fixture is the control — it must stay exit 0.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

LINT = Path(__file__).with_name("component_lint.py").resolve()

# ---------------------------------------------------------------- the fixture

PROMPT = """\
---
id: pa
description: "demo prompt"
---

<role>
r
</role>

<procedure>
p
</procedure>

<io-spec>
## Inputs
- Schema: the seed. Description: what arrives.

## Outcome
o

## Outputs
- Schema: `planning/demo.json` — a JSON object with one top-level string field, `planning-mode`. Description: the stamp the edge reads.
</io-spec>

<permissions>
- Read: the seeded surface.
</permissions>

<restrictions>
- none
</restrictions>

<constraints source="references/ethos.md">
<!-- ethos:start -->

carried line one

carried line two
<!-- ethos:end -->
</constraints>
"""

TASK = """\
---
id: ta
description: "demo task"
---

<task-goal>
g
</task-goal>

<scope>
- Read: x
</scope>

<done-contract>
Done when:
- it is done.
</done-contract>
"""

CHECK_TASK = """\
---
id: check-demo
description: "demo dimension check"
---

<task-goal>
g
</task-goal>

<scope>
- Read: x
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- A demo defect.

Done when, checkable at the edge:
- No finding cites any dimension other than demo.
</done-contract>
"""

FILES = {
    "capabilities/component.md": "---\ndescription: demo\n---\n# demo\n",
    "exposure.csv": ("part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
                     "demo-cap,capability,skill,exhibit,demo.md,a demo capability,\n"),
    "seats.csv": ("seat-id,executor,task,staffing-hints,description\n"
                  "s-ta,pa,ta,,\"Demo seat\"\n"
                  "s-check-demo,pa,check-demo,,\"Check swarm: demo dimension\"\n"),
    "workflows/w/w.csv": ('Seat/workflow,after,i/o,Modality\n'
                          's-ta,,"in: seed; out: draft",agentic\n'
                          's-check-demo,s-ta,"in: draft; out: findings (demo dimension)",agentic\n'),
    "prompts/pa.md": PROMPT,
    "tasks/ta.md": TASK,
    "tasks/check-demo.md": CHECK_TASK,
    "references/ethos.md": ("intro\n<!-- ethos:start -->\n\ncarried line one\n\n"
                            "carried line two\n<!-- ethos:end -->\nouttro\n"),
    "references/exposure.md": (
        "# exposure\n\nThe method vocabulary is CLOSED: **skill · command · rule · hook · "
        "sub-agent · agents.md · config · path · pool** — one method per row.\n"
        "The part-kind vocabulary is CLOSED: **capability · reference · workflow · "
        "task · prompt · tool · plugin/MCP** — one part-kind per row.\n"),
    "references/file-prompt.md": (
        "# prompt file\n\n"
        "**Body — one kind-named XML section per assembled unit, in this order:**\n\n"
        "`<role>` → `<procedure>` → `<resources>` → `<io-spec>` → "
        "`<permissions>` → `<restrictions>` → `<constraints>`\n"),
    "references/file-task.md": (
        "# task file\n\n"
        "**Body — one kind-named XML section per task-serving unit, in this order:**\n\n"
        "`<task-goal>` → `<scope>` → `<done-contract>`\n"),
}

# A stand-in for the optional read-only matrix query.
# being installed. It prints the `cognitive unit` Requirement matrix verbatim.
KG_ROWS = [
    ("role", "n-a", "n-a", "required", "n-a"),
    ("↳ persona", "n-a", "n-a", "required", "n-a"),
    ("↳ agent type", "n-a", "n-a", "required", "n-a"),
    ("procedure", "required", "n-a", "required", "n-a"),
    ("permissions", "n-a", "n-a", "required", "n-a"),
    ("restrictions", "n-a", "n-a", "required", "n-a"),
    ("constraints", "n-a", "n-a", "optional", "n-a"),
    ("i/o spec", "required", "n-a", "required", "n-a"),
    ("↳ input", "required", "n-a", "required", "n-a"),
    ("resources", "n-a", "n-a", "optional", "n-a"),
    ("task goal", "n-a", "n-a", "n-a", "required"),
    ("scope", "n-a", "n-a", "n-a", "required"),
    ("done contract", "n-a", "n-a", "n-a", "required"),
    ("tool", "optional", "n-a", "n-a", "n-a"),
]


def kg_script(rows):
    body = "\n".join("| %s | %s | %s | %s | %s |" % r for r in rows)
    return ("import sys\nprint('''| Cognitive-unit kind | Capability | Reference | "
            "Prompt | Task |\n|---+---+---+---+---|\n" + body + "''')\n")


def build(tmp, edits=None, kg_rows=None):
    """A green component under tmp/mirror/mod/comp, with optional mutations.
    A None value deletes the file."""
    root = Path(tmp) / "mirror" / "mod" / "comp"
    files = dict(FILES)
    files.update(edits or {})
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            continue  # the folder stays, empty — that is the census-gate case
        path.write_text(content, encoding="utf-8")
    (root / "capabilities").mkdir(exist_ok=True)
    kg = Path(tmp) / "fake_kg.py"
    kg.write_text(kg_script(kg_rows or KG_ROWS), encoding="utf-8")
    return root, f"{sys.executable} {kg}"


def run(component, kg, *extra):
    # --home points the vocabulary cross-checks at the FIXTURE's references, so
    # mutating them exercises the self-indictment arms instead of reading the
    # real component this tool ships in.
    proc = subprocess.run(
        [sys.executable, "-B", str(LINT), "--component", str(component),
         "--home", str(component), "--kg", kg, *extra],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def lint(edits=None, kg_rows=None, extra=()):
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, edits, kg_rows)
        return run(component, kg, *extra)


def expect_green(label, edits=None, kg_rows=None, extra=()):
    code, out, err = lint(edits, kg_rows, extra)
    if code != 0:
        raise AssertionError(f"{label}: expected exit 0, got {code}\n{out}\n{err}")
    return out


def expect_red(label, check, needle, edits=None, kg_rows=None, extra=()):
    """The red arm: exit 1, and the named CHECK is the one that fired, with the
    right reason. An assertion on the exit code alone would pass for any
    unrelated failure."""
    code, out, err = lint(edits, kg_rows, extra)
    if code != 1:
        raise AssertionError(f"{label}: expected exit 1, got {code}\n{out}\n{err}")
    fired = [l for l in out.splitlines() if l.strip().startswith("FAIL")]
    matching = [l for l in fired if f"[{check}]" in l and needle in l]
    if not matching:
        raise AssertionError(f"{label}: no FAIL from [{check}] naming {needle!r}\n" + "\n".join(fired))
    return out


# ------------------------------------------------------------------- controls

def test_green_control():
    out = expect_green("green control")
    for needle in ("census: ", "prompts=1", "tasks=2", "seats=2", "manifest-rows=2",
                   "exposure-rows=1", "carried-blocks=1", "dimensions=1", "guards=0",
                   "10 check(s) run, 0 skipped"):
        assert needle in out, f"green control: census missing {needle!r}\n{out}"


def test_census_is_printed_and_gated():
    """A green run over files the tool failed to discover is a FALSE GREEN. An
    empty prompts/ folder is not 'nothing to check' — it is a finding."""
    out = expect_red("census gate", "seat-integrity", "discovered 0 files in prompts/",
                     {"prompts/pa.md": None})
    assert "prompts=0" in out, f"the census must show the zero it gated on\n{out}"


def test_absent_surface_is_skipped_not_passed():
    """Applicability: a component with no prompts/ pool at all (a produced
    workflow's shape) reports SKIP — never a silent pass."""
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"prompts/pa.md": None})
        (component / "prompts").rmdir()
        code, out, _ = run(component, kg, "--check", "interactive-fallback")
        assert code == 0, out
        assert "SKIP interactive-fallback" in out, out
        assert "1 check(s) run" not in out and "0 check(s) run, 1 skipped" in out, out


def test_list_checks():
    proc = subprocess.run([sys.executable, "-B", str(LINT), "--list-checks"],
                          capture_output=True, text=True)
    assert proc.returncode == 0
    for cid in ("exposure-canon", "seat-integrity", "task-no-context", "task-no-capabilities",
                "kind-sections", "dimension-roster", "carried-blocks", "interactive-fallback",
                "fork-discharge"):
        assert cid in proc.stdout, proc.stdout


def test_json_output():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp)
        code, out, _ = run(component, kg, "--json")
        assert code == 0, out
        import json
        data = json.loads(out)
        assert data["fail-count"] == 0 and len(data["checks-run"]) == 10, out
        assert data["census"]["prompts"] == 1, out


# --------------------------------------------------------------------- --all

def build_sweep(tmp, edits_a=None, edits_b=None):
    """A workspace (.rbtv/config marker) holding two components under
    .rbtv/mirror/mod/{comp-a,comp-b} — the tree --all enumerates. Isolated
    from the real repo: workspace_root() walks up from --component and stops
    at THIS .rbtv/config, never reaching HOME's real one."""
    ws = Path(tmp)
    (ws / ".rbtv" / "config").mkdir(parents=True)
    root_a = ws / ".rbtv" / "mirror" / "mod" / "comp-a"
    root_b = ws / ".rbtv" / "mirror" / "mod" / "comp-b"
    for root, edits in ((root_a, edits_a), (root_b, edits_b)):
        files = dict(FILES)
        files.update(edits or {})
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                continue
            path.write_text(content, encoding="utf-8")
        (root / "capabilities").mkdir(exist_ok=True)
    kg = ws / "fake_kg.py"
    kg.write_text(kg_script(KG_ROWS), encoding="utf-8")
    return root_a, root_b, f"{sys.executable} {kg}"


def sweep(anchor, kg, *extra):
    proc = subprocess.run(
        [sys.executable, "-B", str(LINT), "--all", "--component", str(anchor),
         "--home", str(anchor), "--kg", kg, *extra],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_sweep_green_both_components_clean():
    with tempfile.TemporaryDirectory() as tmp:
        root_a, root_b, kg = build_sweep(tmp)
        code, out, err = sweep(root_a, kg)
        assert code == 0, f"{out}\n{err}"
        assert str(root_a) in out and str(root_b) in out, out
        assert "2 component(s), 0 with a finding" in out, out
        assert out.count("0 finding(s), 0 info") == 2, out


def test_sweep_red_names_the_offending_component():
    """One of two components carries a finding (constructed via the same M1
    mutation the single-component red arms use) -> exit non-zero AND the
    sweep names exactly that component, not the clean one."""
    with tempfile.TemporaryDirectory() as tmp:
        bad_exposure = FILES["exposure.csv"] + "x,tool,teleport,,x.py,,\n"
        root_a, root_b, kg = build_sweep(tmp, edits_b={"exposure.csv": bad_exposure})
        code, out, err = sweep(root_a, kg)
        assert code == 1, f"{out}\n{err}"
        fired = [l for l in out.splitlines() if l.strip().startswith("FAIL")]
        assert any(str(root_b) in l and "outside the canon" in l for l in fired), out
        assert not any(str(root_a) in l for l in fired), \
            f"the clean component must carry no FAIL of its own\n{out}"
        assert "2 component(s), 1 with a finding" in out, out


def test_sweep_survives_a_raising_component():
    """ERROR-BOUNDARY ARM. One component raises while it is being linted; the
    OTHER component's result must still be computed and printed, and the run
    must exit 2 (blocked) per the existing contract. Red against the pre-fix
    bare list comprehension: the traceback escapes sweep() and nothing prints.

    The raiser is a seats.csv holding no header row at all — _load_seats()
    indexes rows[0] and raises IndexError inside Component.__init__, i.e. a
    non-Precondition escaping from OUTSIDE any per-check try/except. That is
    exactly the shape the boundary exists for; if that IndexError is ever
    turned into a Precondition, this fixture needs another raiser."""
    with tempfile.TemporaryDirectory() as tmp:
        root_a, root_b, kg = build_sweep(tmp, edits_b={"seats.csv": "\n"})
        code, out, err = sweep(root_a, kg)
        assert "Traceback" not in err, f"the sweep must not unwind:\n{err}"
        assert code == 2, f"expected exit 2 (blocked), got {code}\n{out}\n{err}"
        blocked = [l for l in out.splitlines() if "BLOCKED" in l]
        assert any(str(root_b) in l or "IndexError" in l for l in blocked), \
            f"the raiser must be reported BLOCKED with its message\n{out}"
        assert str(root_b) in out, out
        assert "0 finding(s), 0 info" in out, \
            f"the clean component's result must still be printed\n{out}"
        assert "2 component(s)" in out, out


def test_sweep_json_output():
    with tempfile.TemporaryDirectory() as tmp:
        root_a, root_b, kg = build_sweep(tmp)
        code, out, err = sweep(root_a, kg, "--json")
        assert code == 0, f"{out}\n{err}"
        import json
        data = json.loads(out)
        assert len(data["components"]) == 2 and data["fail-count"] == 0, out


# ---------------------------------------------------------- M1 exposure-canon

def test_red_exposure_method_outside_canon():
    expect_red("M1 bogus method", "exposure-canon", "outside the canon",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,teleport,,x.py,,\n"})


def test_red_exposure_method_missing():
    expect_red("M1 method-less row", "exposure-canon", "empty method",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,,,x.py,,\n"})


def test_red_exposure_path_entry_point_absent():
    expect_red("M1 path entry-point", "exposure-canon", "does not exist on disk",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/nope.py,,\n"})


def test_green_relative_component_path_is_no_escape():
    """A `--component` carrying `..` (the natural form from a nested cwd) used
    to leak its own `..` into every `root / entry-point` join, so EVERY entry
    point read as an escape and the real findings drowned. Drive it relative."""
    with tempfile.TemporaryDirectory() as tmp:
        # the fixture's stock row is method=skill, which never reaches the
        # entry-point arithmetic — a method=path row is what makes this red.
        component, kg = build(tmp, {"exposure.csv":
                                    FILES["exposure.csv"] + "x,tool,path,,seats.csv,,\n",
                                    "demo.md": "---\nexposes-cli:\n  - x\n---\n\n# demo\n"})
        proc = subprocess.run(
            [sys.executable, "-B", str(LINT), "--component", "..",
             "--home", "..", "--kg", kg],
            cwd=str(component / "prompts"), capture_output=True, text=True)
        escapes = [l for l in proc.stdout.splitlines() if "climbs out of its component" in l]
        assert not escapes, "relative --component fabricated escapes:\n" + "\n".join(escapes)
        assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}\n{proc.stdout}{proc.stderr}"


def test_red_exposure_path_row_shape():
    expect_red("M1 path row shape", "exposure-canon", "leaves rbtv-cli empty",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,exhibit,seats.csv,,\n"})


def test_red_exposure_part_kind():
    expect_red("M1 part-kind", "exposure-canon", "outside",
               {"exposure.csv": FILES["exposure.csv"] + "x,gizmo,skill,exhibit,x.md,d,\n"})


# ---- W6 · the seventh column, and the skill -> CLI discovery layer ----------

def test_red_write_root_without_the_danger_marker():
    """The whole point of the column: a write grant is NEVER inferred. An entry
    that merely looks like a path is a refusal, not a grant."""
    expect_red("W6 unmarked write-root", "exposure-canon", "without the danger marker",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,references\n",
                "tool/demo.py": "print('x')\n"})


def test_green_write_root_with_the_danger_marker():
    """…and the marked twin is clean — the red arm above is the MARKER's, not
    the path's."""
    expect_green("W6 marked write-root",
                 {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,!references\n",
                  "tool/demo.py": "print('x')\n",
                  "demo.md": "---\nexposes-cli:\n  - x\n---\n\n# demo\n"})


def test_red_write_root_climbs_out():
    expect_red("W6 write-root escape", "exposure-canon", "climbs with `..`",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,!../elsewhere\n",
                "tool/demo.py": "print('x')\n"})


def test_red_write_root_climbs_out_behind_the_ws_prefix():
    """The prefix does not launder the climb: `!ws:../x` takes the same rule as
    `!../x`, because the prefix is stripped BEFORE the test."""
    expect_red("W6 prefixed write-root escape", "exposure-canon", "climbs with `..`",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,!ws:../elsewhere\n",
                "tool/demo.py": "print('x')\n"})


def test_red_write_root_is_no_directory():
    expect_red("W6 write-root absent", "exposure-canon", "no directory on disk",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,!nowhere\n",
                "tool/demo.py": "print('x')\n"})


def test_red_write_root_on_a_non_path_row():
    expect_red("W6 write-root off a CLI", "exposure-canon", "method=path rows ONLY",
               {"exposure.csv": FILES["exposure.csv"] + "x,reference,rule,,x.md,d,!references\n",
                "x.md": "x\n"})


def test_red_skill_cli_dangling():
    """`skill-cli-dangling` — the skill is the DISCOVERY layer, exposure.csv the
    DECLARATION layer, and a dead reference between them must not reach a
    materialized seat. Refused HERE and at materialize both."""
    expect_red("W6 dangling skill->CLI", "exposure-canon", "skill-cli-dangling",
               {"demo.md": "---\nexposes-cli:\n  - ghost-cli\n---\n\n# demo\n"})


def test_red_skill_cli_points_at_a_non_path_row():
    """It must resolve to a `method=path` row specifically: a skill routing to
    another skill declares no CLI, and would inherit no write-roots."""
    expect_red("W6 skill->CLI wrong method", "exposure-canon", "skill-cli-dangling",
               {"demo.md": "---\nexposes-cli:\n  - demo-cap\n---\n\n# demo\n"})


def test_green_skill_cli_resolves():
    expect_green("W6 skill->CLI resolves",
                 {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,\n",
                  "tool/demo.py": "print('x')\n",
                  "demo.md": "---\nexposes-cli:\n  - x\n---\n\n# demo\n"})


def test_green_path_row_may_carry_description():
    expect_green("path row with a description",
                 {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,Runs demo reports.,\n",
                  "tool/demo.py": "print('x')\n",
                  "demo.md": "---\nexposes-cli:\n  - x\n---\n\n# demo\n"})


def test_red_buried_tool():
    expect_red("tool without skill route", "skill-discovery", "buried tool",
               {"exposure.csv": FILES["exposure.csv"] + "x,tool,path,,tool/demo.py,,\n",
                "tool/demo.py": "print('x')\n"})


def test_green_parent_routes_to_sibling_tool():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"exposure.csv": FILES["exposure.csv"] +
                               "x,tool,path,,tool/demo.py,,\n",
                               "tool/demo.py": "print('x')\n"})
        parent = component.parent / "router"
        parent.mkdir()
        (parent / "exposure.csv").write_text(
            "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
            "parent,capability,skill,,parent.md,Use to run demo reports.,\n", encoding="utf-8")
        (parent / "parent.md").write_text(
            "---\ndescription: Use to run demo reports.\n---\n\n"
            "| Request | Child |\n|---|---|\n| Run a demo report | `mod/comp/x` |\n",
            encoding="utf-8")
        code, out, err = run(component, kg, "--check", "skill-discovery")
        assert code == 0, f"parent route should cover sibling tool: {out}\n{err}"


def test_green_explicit_route_from_other_module():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"exposure.csv": FILES["exposure.csv"] +
                               "x,tool,path,,tool/demo.py,,\n",
                               "tool/demo.py": "print('x')\n"})
        peer = component.parent.parent / "other" / "communication"
        peer.mkdir(parents=True)
        (peer / "exposure.csv").write_text(
            "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
            "slack,reference,skill,,slack.md,Use to send files over Slack.,\n",
            encoding="utf-8")
        (peer / "slack.md").write_text(
            "---\nexposes-cli:\n  - mod/comp/x\n---\n\nUse `x` for files.\n",
            encoding="utf-8")
        code, out, err = run(component, kg, "--check", "skill-discovery")
        assert code == 0, f"cross-component skill route should cover tool: {out}\n{err}"


def test_red_router_description_is_generic():
    expect_red("generic router description", "skill-discovery", "no concrete request",
               {"exposure.csv": FILES["exposure.csv"].replace(
                    "a demo capability", "Routes requests to child skills"),
                "demo.md": "---\ndescription: Routes requests to child skills.\n---\n\n"
                           "| Request | Child |\n|---|---|\n| Run a demo report | `demo-child` |\n"})


def test_red_router_without_table_has_generic_description():
    expect_red("generic router without table", "skill-discovery", "no concrete request",
               {"exposure.csv": FILES["exposure.csv"].replace(
                    "a demo capability", "A router for child skills"),
                "demo.md": "---\ndescription: A router for child skills.\n---\n\n# demo\n"})


def test_green_router_description_names_request():
    expect_green("router names a request",
                 {"exposure.csv": FILES["exposure.csv"].replace(
                      "a demo capability", "Use to run demo reports"),
                  "demo.md": "---\ndescription: Use to run demo reports.\n---\n\n"
                             "| Request | Child |\n|---|---|\n| Run a demo report | `demo-child` |\n"})


def test_red_exposure_canon_crosscheck():
    """The hardcoded vocabulary and the reference that owns it police each
    other: drop a value from the guide and the tool indicts ITSELF."""
    expect_red("M1 canon cross-check", "exposure-canon", "component_lint.py",
               {"references/exposure.md": FILES["references/exposure.md"].replace(" · path", "")})


def test_red_exposure_part_kind_crosscheck():
    """Same policing for the part-kind canon: drop a value from the guide and
    the tool indicts ITSELF, naming the two disagreeing homes."""
    expect_red("M1 part-kind cross-check", "exposure-canon", "component_lint.py",
               {"references/exposure.md": FILES["references/exposure.md"].replace(
                   " · tool", "")})


def test_green_part_kind_crosscheck_agrees_either_order():
    """The green arm, and the discriminator: the part-kind run is found by the
    value it names, not by being first — swap the two runs and both canons
    still resolve to their own list."""
    guide = FILES["references/exposure.md"]
    method_line, kind_line = guide.splitlines(keepends=True)[-2:]
    expect_green("M1 part-kind cross-check agrees",
                 {"references/exposure.md": guide.replace(
                     method_line + kind_line, kind_line + method_line)})


def test_red_exposure_duplicate_part_id():
    expect_red("M1 duplicate part-id", "exposure-canon", "duplicate part-id",
               {"exposure.csv": FILES["exposure.csv"] + "demo-cap,capability,skill,exhibit,d.md,again,\n"})


# ---------------------------------------------------------- M2 seat-integrity

def test_red_seat_executor_dangling():
    expect_red("M2 dangling executor", "seat-integrity", "has no prompts/",
               {"seats.csv": FILES["seats.csv"].replace("s-ta,pa,ta", "s-ta,ghost,ta")})


def test_red_seat_task_dangling():
    expect_red("M2 dangling task", "seat-integrity", "has no tasks/",
               {"seats.csv": FILES["seats.csv"].replace("s-ta,pa,ta,", "s-ta,pa,ghost,")})


def test_red_orphan_pool_file():
    expect_red("M2 orphan", "seat-integrity", "orphan task file",
               {"tasks/spare.md": TASK.replace("id: ta", "id: spare")})


def test_red_id_mismatch():
    expect_red("M2 id mismatch", "seat-integrity", "does not match the filename stem",
               {"prompts/pa.md": PROMPT.replace("id: pa", "id: pb")})


def test_red_manifest_row_dangling():
    expect_red("M2 manifest row", "seat-integrity", "resolves to no seat id",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace("s-ta,,", "s-ghost,,")})


def test_red_after_ref_dangling():
    expect_red("M2 after ref", "seat-integrity", "resolves to no manifest row",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   "s-check-demo,s-ta,", "s-check-demo,s-nobody,")})


def test_red_modality_outside_vocabulary():
    expect_red("M2 modality", "seat-integrity", "outside",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   '"in: seed; out: draft",agentic', '"in: seed; out: draft",vibes')})


def test_red_cycle():
    expect_red("M2 cycle", "seat-integrity", "cyclic",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   "s-ta,,", "s-ta,s-check-demo,")})


def test_guard_alternation_inside_one_bracket_survives():
    """`ref[f=a|b]` is ONE guarded ref, not two limbs. A naive split on '|'
    shreds it into unresolvable refs — this arm goes red if that regresses."""
    expect_green("M2 guard alternation", {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
        "s-check-demo,s-ta,", "s-check-demo,s-ta[planning-mode=full|collapsed],")})
    expect_red("M2 guard alternation ref", "seat-integrity", "resolves to no manifest row",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   "s-check-demo,s-ta,", "s-check-demo,s-nobody[planning-mode=full|collapsed],")})


def test_red_no_manifest_seat_unsanctioned():
    """A seat outside the manifest with no sub-agent/pool exposure row on its
    executor is a FAIL, not an INFO (owner-ruled, planning-v4 D22)."""
    expect_red("M2 unsanctioned no-manifest seat", "seat-integrity", "sanctioning exposure row",
               {"seats.csv": FILES["seats.csv"] + 's-loose,pa,ta,,"Loose seat"\n'})


def test_green_no_manifest_seat_pool_sanctioned():
    """The same seat with a pool exposure row on its executor is sanctioned —
    silent, and counted in the census."""
    out = expect_green("M2 pool-sanctioned no-manifest seat", {
        "seats.csv": FILES["seats.csv"] + 's-loose,pa,ta,,"Loose seat"\n',
        "exposure.csv": FILES["exposure.csv"] + "pa,prompt,pool,,prompts/pa.md,,\n"})
    assert "sanctioned-no-manifest=1" in out, f"census must count the sanction\n{out}"


# ------------------------------------------------------------ M3 task-no-context

def test_red_task_context_field_present():
    """W6/R3 — `context:` is DELETED from the task schema. The old M3 check
    (list shape + dangling refs) is RETIRED rather than left in place: over a
    field no author may write it could only ever pass."""
    expect_red("M3 deleted field", "task-no-context", "DELETED task field",
               {"tasks/ta.md": TASK.replace(
                   "id: ta\n", "id: ta\ncontext:\n  - references/file-task.md\n")})


def test_red_task_context_empty_list_still_present():
    """An empty list is still the field. `capabilities: []` red-arms the same
    way — a retired key is absent, not merely unused."""
    expect_red("M3 deleted field, empty", "task-no-context", "DELETED task field",
               {"tasks/ta.md": TASK.replace("id: ta\n", "id: ta\ncontext: []\n")})


# ---- Component.resolve — now reached through carried-blocks (M7) only --------

def test_carried_source_resolves_through_extra_root():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"prompts/pa.md": PROMPT.replace(
            'source="references/ethos.md"', 'source="elsewhere/ethos.md"')})
        code, out, _ = run(component, kg)
        assert code == 1 and "does not resolve" in out, out
        extra = Path(tmp) / "outside"
        (extra / "elsewhere").mkdir(parents=True)
        (extra / "elsewhere" / "ethos.md").write_text(
            (Path(component) / "references" / "ethos.md").read_text(encoding="utf-8"),
            encoding="utf-8")
        code, out, _ = run(component, kg, "--root", str(extra))
        assert code == 0, out


def test_carried_source_resolves_from_the_workspace_root_with_ws_prefix():
    """`ws:` is the ONE sanctioned way out of the component (D33): the rest is a
    path from the first ancestor holding `.rbtv/config/`. Red arm first — with no
    such ancestor there is no workspace, so the same ref must NOT resolve."""
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"prompts/pa.md": PROMPT.replace(
            'source="references/ethos.md"', 'source="ws:outside/ethos.md"')})
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (outside / "ethos.md").write_text(
            (Path(component) / "references" / "ethos.md").read_text(encoding="utf-8"),
            encoding="utf-8")
        code, out, _ = run(component, kg)
        assert code == 1 and "does not resolve" in out, out
        (Path(tmp) / ".rbtv" / "config").mkdir(parents=True)
        code, out, _ = run(component, kg)
        assert code == 0, out


def test_bare_out_of_component_ref_still_does_not_resolve():
    """The plain-path root list was NOT widened: only `ws:` leaves the component,
    so a bare ref to the very same file stays a finding."""
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"prompts/pa.md": PROMPT.replace(
            'source="references/ethos.md"', 'source="outside/ethos.md"')})
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (outside / "ethos.md").write_text("x", encoding="utf-8")
        (Path(tmp) / ".rbtv" / "config").mkdir(parents=True)
        code, out, _ = run(component, kg)
        assert code == 1 and "does not resolve" in out, out


# ------------------------------------------------------ M4 task-no-capabilities

def test_red_task_capabilities_field_present():
    expect_red("M4 retired field", "task-no-capabilities", "retired task field",
               {"tasks/ta.md": TASK.replace("id: ta\n", "id: ta\ncapabilities: []\n")})


# ----------------------------------------------------------- M5 kind-sections

def test_red_required_section_absent():
    expect_red("M5 missing required", "kind-sections", "<permissions> is required",
               {"prompts/pa.md": PROMPT.replace("<permissions>\n- Read: the seeded surface.\n</permissions>\n\n", "")})


def test_red_duplicate_section():
    """The latent defect kind-constraints.md step 5 can invite: a second
    plain <constraints> beside the carried one."""
    expect_red("M5 duplicate section", "kind-sections", "appears 2 times",
               {"prompts/pa.md": PROMPT + "\n<constraints>\nseat-specific\n</constraints>\n"})


def test_red_forbidden_section_on_task():
    expect_red("M5 n-a section", "kind-sections", "n-a for a task file",
               {"tasks/ta.md": TASK + "\n<io-spec>\nnever on a task\n</io-spec>\n"})


def test_red_section_order():
    expect_red("M5 order", "kind-sections", "out of canonical order",
               {"prompts/pa.md": PROMPT.replace("<role>\nr\n</role>\n\n<procedure>\np\n</procedure>",
                                                "<procedure>\np\n</procedure>\n\n<role>\nr\n</role>")})


def test_red_matrix_crosscheck():
    """Hardcoded matrix vs the KG record: make the record disagree and the tool
    indicts ITSELF rather than silently trusting its copy."""
    rows = [r if r[0] != "constraints" else ("constraints", "n-a", "n-a", "required", "n-a")
            for r in KG_ROWS]
    expect_red("M5 matrix cross-check", "kind-sections", "requirement-matrix cross-check",
               kg_rows=rows)


def test_red_order_crosscheck():
    expect_red("M5 order cross-check", "kind-sections", "section-order cross-check",
               {"references/file-task.md": (
                   "# task file\n\n"
                   "**Body — one kind-named XML section per task-serving unit, in this order:**\n\n"
                   "`<scope>` → `<task-goal>` → `<done-contract>`\n")})


def test_green_arrow_in_unrelated_bullet():
    """Red-first arm for the guide_order anchor (task 7.646): an unrelated
    bullet carrying three backticked angle-tags plus an arrow must NOT be
    mistaken for the section-order line. Observed live: file-prompt.md's
    `exposes` bullet ("method → exposure.csv part-ids") won the first-match
    scan the moment it mentioned a third tag, and the check indicted the
    hardcoded constant with a bogus disagreement."""
    guide = (
        "# prompt file\n\n"
        "- `exposes` — method → exposure.csv part-ids; realized for "
        "`<role>` `<procedure>` `<resources>` alike\n\n"
        "**Body — one kind-named XML section per assembled unit, in this order:**\n\n"
        "`<role>` → `<procedure>` → `<resources>` → `<io-spec>` → "
        "`<permissions>` → `<restrictions>` → `<constraints>`\n")
    expect_green("M5 unrelated-bullet arrow", {"references/file-prompt.md": guide})


def test_kg_unavailable_blocks_only_its_own_check():
    """A precondition broken INSIDE a check blocks THAT check — it never unwinds
    past the print block and discards the census plus everything the earlier
    checks already found. Exit stays 2: blocked is not skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        component, _ = build(tmp, {"tasks/ta.md": TASK.replace(
            "id: ta\n", "id: ta\ncontext: []\n")})
        code, out, _err = run(component, f"{sys.executable} /nonexistent/kg.py")
        assert code == 2, f"a KG the cross-check cannot read is exit 2, got {code}\n{out}"
        assert "census: " in out, f"the census must survive a blocked check\n{out}"
        assert "BLOCKED kind-sections" in out, out
        assert "KG query failed" in out, out
        assert "1 blocked" in out, out
        # the load-bearing arm: a finding from a check that ran BEFORE the
        # blocked one is still reported, not discarded with the abort
        assert "[task-no-context]" in out and "DELETED task field" in out, out


# -------------------------------------------------------- M10 dimension-roster

def test_green_no_check_tasks_no_roster():
    # 7.625: a component with no check-* tasks at all (master) has no
    # roster to check — the zero-roster tripwire stays quiet.
    expect_green("no check swarm", {
        "tasks/check-demo.md": None,
        "seats.csv": FILES["seats.csv"].replace(
            "s-check-demo,pa,check-demo,,\"Check swarm: demo dimension\"\n", ""),
        "workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
            's-check-demo,s-ta,"in: draft; out: findings (demo dimension)",agentic\n', "")})


def test_green_lone_pool_check_task_no_swarm():
    # The sign of a check SWARM is a check-* task held by a MANIFEST ROW, not a
    # check-* task STEM. planning's `check-unblocked` is the live instance: a
    # judge-pool seat, sanctioned by a method=pool exposure row, holding no
    # manifest node and carrying no dimension clause. The tripwire stays quiet.
    expect_green("lone pool check task", {
        "tasks/check-demo.md": TASK.replace("id: ta", "id: check-demo"),
        "exposure.csv": FILES["exposure.csv"] + "pb,prompt,pool,,prompts/pb.md,,\n",
        "prompts/pb.md": PROMPT.replace("id: pa", "id: pb"),
        "seats.csv": FILES["seats.csv"].replace(
            "s-check-demo,pa,check-demo,,\"Check swarm: demo dimension\"\n",
            "s-check-demo,pb,check-demo,,\"Judge pool: demo\"\n"),
        "workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
            's-check-demo,s-ta,"in: draft; out: findings (demo dimension)",agentic\n', "")})


def test_red_check_task_without_dimension_clause():
    # 7.625: check-* stems exist but the clause parse finds none — the scoped
    # vacuity tripwire fires.
    expect_red("M10 clause parse broke", "dimension-roster", "0 carry a dimension clause",
               {"tasks/check-demo.md": CHECK_TASK.replace(
                   "- No finding cites any dimension other than demo.\n", "")})


def test_red_kill_criteria_empty():
    expect_red("M10 empty kill criteria", "dimension-roster", "kill-criteria block is empty",
               {"tasks/check-demo.md": CHECK_TASK.replace("- A demo defect.\n", "")})


def test_red_dimension_not_named_in_seat():
    expect_red("M10 seat description", "dimension-roster", "names no dimension",
               {"seats.csv": FILES["seats.csv"].replace("Check swarm: demo dimension",
                                                        "Check swarm: renamed dimension")})


def test_red_dimension_not_named_in_manifest():
    expect_red("M10 manifest i/o", "dimension-roster", "names no dimension",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   "findings (demo dimension)", "findings (renamed dimension)")})


def test_red_check_row_with_no_dimension_clause():
    """A check row added to the swarm whose task declares no dimension at all."""
    expect_red("M10 undeclared check row", "dimension-roster", "declares no dimension clause", {
        "tasks/check-other.md": CHECK_TASK.replace("id: check-demo", "id: check-other").replace(
            "- No finding cites any dimension other than demo.", "- it is done."),
        "seats.csv": FILES["seats.csv"] + 's-check-other,pa,check-other,,"Check swarm: other dimension"\n',
        "workflows/w/w.csv": FILES["workflows/w/w.csv"]
        + 's-check-other,s-ta,"in: draft; out: findings (other dimension)",agentic\n'})


def test_dimension_roster_without_seats_csv():
    """HALF-FED ARM. `dimension-roster` needs ("tasks","seats.csv") and run()
    starts it when ANY need is present — so tasks-with-dimension-clauses plus an
    ABSENT seats.csv reaches the body with c.seats still None. The pairing half
    is then not applicable, not a finding; only the task-side kill-criteria half
    can be checked. Red against the pre-fix code with an unhandled TypeError
    ('NoneType' object is not subscriptable)."""
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"seats.csv": None})
        assert not (component / "seats.csv").exists(), "the arm must actually drop seats.csv"
        code, out, err = run(component, kg, "--check", "dimension-roster")
        assert "Traceback" not in err, f"the check must not raise:\n{err}"
        assert code == 0, f"expected exit 0, got {code}\n{out}\n{err}"
        assert not [l for l in out.splitlines() if l.strip().startswith("FAIL")], out


def test_dimension_roster_empty_seats_csv_still_fails():
    """The vacuity tripwire the guard must NOT swallow: seats.csv PRESENT but
    carrying no rows is a real census failure, not 'not applicable'."""
    expect_red("M10 present-but-empty seats.csv", "dimension-roster",
               "paired by 0 seat rows",
               {"seats.csv": "seat-id,executor,task,staffing-hints,description\n"},
               extra=("--check", "dimension-roster"))


# ---------------------------------------------------------- M7 carried-blocks

def test_red_carried_block_drift():
    expect_red("M7 drift", "carried-blocks", "DRIFTED",
               {"prompts/pa.md": PROMPT.replace("carried line two", "carried line CHANGED")})


def test_red_carried_block_swallowed_blank_line():
    """Whitespace drift is drift — the failure a prose eyeball never catches."""
    expect_red("M7 swallowed blank", "carried-blocks", "DRIFTED",
               {"prompts/pa.md": PROMPT.replace("\n\ncarried line two", "\ncarried line two")})


def test_green_carrier_local_below_end_marker():
    """Marker-anchored: content below the end marker is carrier-local, not drift."""
    expect_green("M7 local tail",
                 {"prompts/pa.md": PROMPT.replace("<!-- ethos:end -->\n",
                                                  "<!-- ethos:end -->\n- seat-specific bound\n")})


def test_red_carrier_markers_absent():
    expect_red("M7 carrier markers", "carried-blocks", "carrier lacks",
               {"prompts/pa.md": PROMPT.replace("<!-- ethos:start -->\n", "").replace("<!-- ethos:end -->\n", "")})


def test_red_carried_block_markers_absent():
    expect_red("M7 markers", "carried-blocks", "malformed or absent",
               {"references/ethos.md": "no markers here\n"})


def test_red_carried_block_source_dangling():
    expect_red("M7 source", "carried-blocks", "source does not resolve",
               {"prompts/pa.md": PROMPT.replace('source="references/ethos.md"',
                                                'source="references/gone.md"')})


def test_red_carried_block_near_miss_attribute():
    expect_red("M7 near miss", "carried-blocks", "non-double-quoted form",
               {"prompts/pa.md": PROMPT.replace('source="references/ethos.md"',
                                                "source='references/ethos.md'")})


def test_carried_block_generalizes_beyond_ethos():
    """M7's whole point: ANY tag, ANY source, ANY anchor — not just the
    ethos-specific pair the superseded checker hardcoded."""
    body = ("Kill criteria — the dimension's whole law; any hit is a FAIL finding:\n"
            "- A demo defect.\n\n"
            "Done when, checkable at the edge:\n"
            "- No finding cites any dimension other than demo.")
    shared = f"prefix\n<!-- killset:start -->\n{body}\n<!-- killset:end -->\nouttro\n"
    carried = CHECK_TASK.replace(
        "<done-contract>",
        '<done-contract source="references/shared.md#killset">\n<!-- killset:start -->', 1).replace(
        "</done-contract>", "<!-- killset:end -->\n</done-contract>", 1)
    # a synced copy of a NON-ethos block, under a NON-constraints tag, via an ANCHOR
    expect_green("M7 generalized sync", {"references/shared.md": shared,
                                         "tasks/check-demo.md": carried})
    # and the same block drifts red
    expect_red("M7 generalized drift", "carried-blocks", "DRIFTED",
               {"references/shared.md": shared,
                "tasks/check-demo.md": carried.replace("- A demo defect.", "- A DIFFERENT defect.")})


# ----------------------------------------------------- M9 interactive-fallback

def test_red_flag_without_fallback():
    expect_red("M9 missing fallback", "interactive-fallback", "no fallback: field",
               {"prompts/pa.md": PROMPT.replace('description: "demo prompt"',
                                                'description: "demo prompt"\nhuman-interactive: yes')})


def test_red_fallback_outside_vocabulary():
    expect_red("M9 bad arm", "interactive-fallback", "outside",
               {"prompts/pa.md": PROMPT.replace(
                   'description: "demo prompt"',
                   'description: "demo prompt"\nhuman-interactive: yes\nfallback: wing-it')})


def test_red_fallback_without_flag_or_modality():
    expect_red("M9 orphan fallback", "interactive-fallback",
               "neither human-interactive: yes nor an",
               {"prompts/pa.md": PROMPT.replace('description: "demo prompt"',
                                                'description: "demo prompt"\nfallback: park')})


def test_red_interactive_row_without_flag():
    expect_red("M9 modality without flag", "interactive-fallback",
               "carries no human-interactive: yes",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   '"in: seed; out: draft",agentic', '"in: seed; out: draft",interactive')})


def test_green_flag_with_legal_arm():
    expect_green("M9 green triple", {"prompts/pa.md": PROMPT.replace(
        'description: "demo prompt"',
        'description: "demo prompt"\nhuman-interactive: yes\nfallback: park')})


BLOCK_AND_QUEUE = PROMPT.replace(
    'description: "demo prompt"',
    'description: "demo prompt"\nhuman-interactive: yes\nfallback: block-and-queue')


def test_red_block_and_queue_without_autonomous_arm():
    """The arm IS the workaround: a block-and-queue procedure that only blocks
    has no autonomous path at all."""
    expect_red("M9 no autonomous arm", "interactive-fallback", "Autonomous arm",
               {"prompts/pa.md": BLOCK_AND_QUEUE})


def test_green_block_and_queue_with_autonomous_arm():
    expect_green("M9 autonomous arm present", {"prompts/pa.md": BLOCK_AND_QUEUE.replace(
        "<procedure>\np\n", "<procedure>\np\n2. Autonomous arm — derive and disclose.\n")})


# --------------------------------------------------------- M12 fork-discharge
# The guard `pred[key=value]` is discharged by READING `key` off a `.json`
# artifact the predecessor's prompt declares under `## Outputs`. The fixture
# prompt declares `planning/demo.json` stating `planning-mode`.

GUARDED = FILES["workflows/w/w.csv"].replace("s-check-demo,s-ta,",
                                             "s-check-demo,s-ta[planning-mode=full],")


def test_green_fork_guard_served():
    out = expect_green("M12 served guard", {"workflows/w/w.csv": GUARDED})
    assert "guards=1" in out, f"the census must count what it checked\n{out}"


def test_green_fork_alternate_limb_by_limb():
    """An alternate is checked limb by limb: the guarded limb needs its key
    served, the bare limb declares no field and needs nothing."""
    expect_green("M12 alternate limbs", {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
        "s-check-demo,s-ta,", "s-check-demo,s-ta[planning-mode=full]|s-ta,")})


def test_red_fork_guard_key_not_stated():
    expect_red("M12 unserved key", "fork-discharge", "'use-case'",
               {"workflows/w/w.csv": FILES["workflows/w/w.csv"].replace(
                   "s-check-demo,s-ta,", "s-check-demo,s-ta[use-case=optimize],")})


def test_red_fork_predecessor_declares_prose():
    """THE seam this check exists for: the predecessor states its output as prose
    the edge runner's parser cannot read, so it declares nothing and no guard
    over it can ever be served — the fork neither opens nor dies."""
    prose = PROMPT.replace(
        "## Outputs\n- Schema: `planning/demo.json` — a JSON object with one "
        "top-level string field, `planning-mode`. Description: the stamp the edge reads.\n",
        "- **output** — schema: a planning-mode stamp. description: the stamp the edge reads.\n")
    assert "## Outputs" not in prose, "the prose arm must actually drop the heading"
    expect_red("M12 prose outputs", "fork-discharge", "no `## Outputs` heading",
               {"prompts/pa.md": prose, "workflows/w/w.csv": GUARDED})


def test_red_fork_no_json_declared():
    expect_red("M12 no json output", "fork-discharge", "declares no `.json` artifact",
               {"prompts/pa.md": PROMPT.replace("`planning/demo.json`", "`planning/demo.md`"),
                "workflows/w/w.csv": GUARDED})


# -------------------------------------------------------------- preconditions

def test_missing_component_is_exit_2():
    proc = subprocess.run([sys.executable, "-B", str(LINT), "--component", "/does/not/exist"],
                          capture_output=True, text=True)
    assert proc.returncode == 2, proc.returncode
    assert "not a directory" in proc.stderr, proc.stderr


def test_broken_frontmatter_is_exit_2():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"prompts/pa.md": "no frontmatter at all\n<role>\nr\n</role>\n"})
        code, _out, err = run(component, kg)
        assert code == 2, f"expected exit 2, got {code}: {err}"
        assert "no frontmatter" in err, err


def test_green_seats_header_extra_trailing_columns():
    # 7.625: master appends cage-grants,rw-paths after the shared five —
    # a superset header lints; rows are read from the shared prefix.
    expect_green("seats extra columns",
                 {"seats.csv": FILES["seats.csv"].replace(
                     "seat-id,executor,task,staffing-hints,description",
                     "seat-id,executor,task,staffing-hints,description,cage-grants,rw-paths")})


def test_diverged_seats_header_prefix_is_exit_2():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp, {"seats.csv": FILES["seats.csv"].replace(
            "seat-id,executor,task", "seat-id,occupant,task")})
        code, _out, err = run(component, kg)
        assert code == 2 and "unrecognized header" in err, (code, err)


def test_unknown_check_id_is_exit_2():
    with tempfile.TemporaryDirectory() as tmp:
        component, kg = build(tmp)
        code, _out, err = run(component, kg, "--check", "nonesuch")
        assert code == 2 and "unknown check id" in err, err


def test_home_rbtv_is_not_a_workspace_without_install_json():
    """Home's `~/.rbtv/` is the per-user runtime (rbtv CLAUDE.md, Linux AND
    Windows rule 6): a home holding only `.rbtv/config/install-index.json` is
    never the workspace; with a real `install.json` it is. Called in-process
    with Path.home patched. A real ancestor above the fake home (on Windows,
    the machine's own home) must not decide the result, so the red arm asserts
    only that the fake home was NOT chosen."""
    import importlib.util
    from unittest import mock
    spec = importlib.util.spec_from_file_location("component_lint_under_test", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp).resolve()
        config = home / ".rbtv" / "config"
        config.mkdir(parents=True)
        (config / "install-index.json").write_text("{}", encoding="utf-8")
        start = home / "mirror" / "mod" / "comp"
        start.mkdir(parents=True)
        with mock.patch.object(Path, "home", return_value=home):
            assert mod.workspace_root(start) != home, \
                "home holding only install-index.json was taken as the workspace"
            (config / "install.json").write_text("{}", encoding="utf-8")
            assert mod.workspace_root(start) == home, \
                "home holding a real install.json must be the workspace"


def main():
    os.chdir(tempfile.gettempdir())
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  PASS: {test.__name__}")
    print(f"PASS ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
