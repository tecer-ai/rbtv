"""verify_access's cases must be able to FAIL — proven, not asserted.

The tool's own `selftest` runs each case green and breaks its INPUT to prove the
case reddens. These tests go one level out and break the TOOL: each mutation
below removes one contract, and the case that guards that contract must be the
one that goes red. A case no mutation can redden is not a case.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2]
TOOL = WORKFLOW / "tools" / "verify_access.py"
SEAMS = WORKFLOW / "seams"

# (case name, the source this removes, what replaces it)
MUTANTS = [
    ("folder:legacy-meet-recordings", "for name in names:",
     'for name in (names[:0] if names and names[0].endswith("Legacy") else names):'),
    ("folder:google-meet-tree", "for name in names:",
     'for name in (names[:0] if names and names[0].endswith("Tree") else names):'),
    ("folder:tactiq-autosave", "for name in names:",
     'for name in (names[:0] if names and names[0].endswith("Tactiq") else names):'),
    ("precondition:meet-transcription-config",
     'for token in tokens:', 'return {"verdict": "live", "detail": "assumed"}\n    for token in tokens:'),
    ("precondition:tactiq-naming-discriminator",
     "if len(matched) == len(names):", "if True:"),
    ("id-not-name", 'raise DriverError("a matching folder carries no Drive id")',
     'folder_id = hit.get("name") or "?"'),
    ("call-failure-is-not-dead",
     'except DriverError as exc:\n            verdict["errors"][account] = scrub(str(exc))',
     'except DriverError as exc:\n            verdict["accounts"][account] = '
     '{"preconditions": {i: {"verdict": "dead"} for i in ids}, "sources": []}'),
    ("seam-conformance", '"generated-at": verdict["verified-at"],',
     '"generated-at": verdict["verified-at"], "stowaway": 1,'),
    ("no-half-map", 'if verdict["verdict"] != "pass":\n        return written',
     "if False:\n        return written"),
    ("accounts-from-config", "for account in accounts:",
     'for account in (list(accounts) + ["acct-a"] if "acct-a" not in accounts else accounts):'),
    ("ids-from-seams",
     'required = schema.get("$defs", {}).get("precondition-verdicts", {}).get("required")',
     'required = ["legacy-meet-recordings-folder", "google-meet-tree", '
     '"tactiq-autosave-folder", "meet-transcription-config", '
     '"tactiq-naming-discriminator"] if True else None'),
    ("one-folder-per-layout", "        if ref in by_ref:", "        if False:"),
    ("call-log-carries-no-paths", 'return ABSPATH.sub("<path>", (text or "").strip())',
     'return (text or "").strip()'),
]


def run_selftest(tool: Path, seams: Path):
    proc = subprocess.run([sys.executable, str(tool), "selftest", "--seams", str(seams)],
                          capture_output=True, text=True)
    reddened = sorted(set(re.findall(r"^  FAIL  (\S+)", proc.stdout, re.M)))
    return proc, reddened


def test_selftest_is_green_and_discriminating():
    proc, reddened = run_selftest(TOOL, SEAMS)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "discriminating: True" in proc.stdout
    assert reddened == []


def test_every_case_is_named_by_the_selftest():
    proc, _ = run_selftest(TOOL, SEAMS)
    named = set(re.findall(r"^  PASS  (\S+)", proc.stdout, re.M))
    assert {arm for arm, _, _ in MUTANTS} <= named, named


@pytest.mark.parametrize("arm,old,new", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_case_reddens_when_its_contract_is_removed(arm, old, new, tmp_path):
    source = TOOL.read_text(encoding="utf-8")
    assert old in source, f"mutation anchor for {arm} no longer exists in the tool"
    shutil.copytree(SEAMS, tmp_path / "seams")
    (tmp_path / "tools").mkdir()
    mutant = tmp_path / "tools" / "verify_access.py"
    mutant.write_text(source.replace(old, new, 1), encoding="utf-8")

    proc, reddened = run_selftest(mutant, tmp_path / "seams")
    assert proc.returncode != 0, f"{arm} survived its mutation:\n{proc.stdout}"
    assert arm in reddened, f"{arm} did not redden; reddened={reddened}\n{proc.stdout}"


def test_tool_probes_nothing_the_owner_attested():
    """The attestation boundary, checked against this tool and this test file.

    The patterns are IMPORTED from the seam validator rather than restated here:
    one source for the boundary, and a copy of them in this file would itself be
    a hit when the validator's own grep arm sweeps the workflow tree.
    """
    sys.path.insert(0, str(TOOL.parent))
    import validate_seams

    hits = []
    for path in (TOOL, Path(__file__)):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name, pattern in validate_seams.FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    hits.append(f"{path.name}:{lineno} [{name}]: {line.strip()}")
    assert hits == [], hits


def test_no_absolute_path_is_written_into_an_artifact(tmp_path):
    """A token store or a host can ride inside a tool's error text; scrub catches it."""
    sys.path.insert(0, str(TOOL.parent))
    import verify_access

    log = verify_access.CallLog()
    log.record("acct-a", "drive.search", 1,
               "RefreshError: the stored grant at /fixture/redaction-probe is invalid")
    text = log.text()
    assert "/fixture/" not in text
    assert "<path>" in text
