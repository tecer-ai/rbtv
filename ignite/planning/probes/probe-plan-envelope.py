#!/usr/bin/env python3
"""probe-plan-envelope — the planning-stage producer of bound-commit envelope.json.

evidence-class: FIXTURE. A scratch git repo is the plan-artifacts tree. The REAL
`plan_envelope.py` writer authors `envelope.json`; `path_b.bound_envelope_fillins`
reads it back from the bound commit. Nothing here births a live goal.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PLANNING = _HERE.parent
sys.path.insert(0, str(_PLANNING))

import path_b  # noqa: E402
import plan_envelope  # noqa: E402

WRITER = _PLANNING / "plan_envelope.py"
out_path = _HERE / "probe-plan-envelope.out"


def out(text):
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")


checks = []


def check(name, pass_, detail=""):
    checks.append(pass_)
    out(f"{'PASS' if pass_ else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def git(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def run_writer(args):
    try:
        proc = subprocess.run(
            [sys.executable, "-B", str(WRITER), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except OSError as exc:
        return 99, "", str(exc)


def main():
    out_path.write_text("", encoding="utf-8")
    out("COMMAND: python3 -B ignite/planning/probes/probe-plan-envelope.py")
    out("evidence-class: FIXTURE scratch git repo; REAL plan_envelope writer; REAL bound_envelope_fillins")

    with tempfile.TemporaryDirectory(prefix="plan-envelope-probe-") as tmp_s:
        tmp = Path(tmp_s)
        artifacts = tmp / "planning"
        artifacts.mkdir()
        code, stdout, stderr = run_writer([
            "--plan-artifacts", str(artifacts),
            "--credential-name", "ELEVENLABS_API_KEY",
            "--json",
        ])
        written = artifacts / "envelope.json"
        body = json.loads(written.read_text(encoding="utf-8")) if written.is_file() else None
        check(
            "P1 writer authors credentialNames",
            code == 0 and body == {"credentialNames": ["ELEVENLABS_API_KEY"]},
            f"code={code} body={body} stderr={stderr[:200]!r} stdout_ok={bool(stdout)}",
        )

        git(artifacts, "init")
        git(artifacts, "config", "user.email", "probe@example")
        git(artifacts, "config", "user.name", "probe")
        git(artifacts, "add", "envelope.json")
        git(artifacts, "commit", "-m", "plan envelope with ELEVENLABS_API_KEY")
        sha = git(artifacts, "rev-parse", "HEAD").stdout.strip()
        shown = git(artifacts, "show", f"{sha}:envelope.json").stdout
        check(
            "P2 bound commit carries the artifact",
            sha and json.loads(shown) == {"credentialNames": ["ELEVENLABS_API_KEY"]},
            f"sha={sha} path={written} show={shown.strip()}",
        )

        pkg = {
            "bound_commit": sha,
            "plan_artifacts": str(artifacts),
            "git_dir": str(artifacts),
            "execution_goal": "test-cred-injection",
        }
        fillins = path_b.bound_envelope_fillins(pkg)
        check(
            "P3 bound_envelope_fillins reads producer output",
            fillins == {"credentialNames": ["ELEVENLABS_API_KEY"]},
            f"fillins={fillins}",
        )

        code_bad, out_bad, _ = run_writer([
            "--plan-artifacts", str(tmp / "empty"),
            "--credential-name", "not a name",
        ])
        refused = json.loads(out_bad) if out_bad.strip().startswith("{") else {}
        check(
            "P4 bad credential name refuses",
            code_bad == 2 and refused.get("ok") is False
            and (refused.get("refusal") or {}).get("code") == "bad-credential-name",
            f"code={code_bad} refused={refused}",
        )

        missing = tmp / "no-envelope"
        missing.mkdir()
        git(missing, "init")
        git(missing, "config", "user.email", "probe@example")
        git(missing, "config", "user.name", "probe")
        (missing / "README").write_text("no envelope\n", encoding="utf-8")
        git(missing, "add", ".")
        git(missing, "commit", "-m", "plan without envelope")
        sha_miss = git(missing, "rev-parse", "HEAD").stdout.strip()
        none = path_b.bound_envelope_fillins({
            "bound_commit": sha_miss,
            "plan_artifacts": str(missing),
            "git_dir": str(missing),
            "execution_goal": "test-no-envelope",
        })
        check(
            "P5 absent artifact is None, not a refusal",
            none is None,
            f"none={none}",
        )

        out(f"FIXTURE_BOUND_COMMIT={sha}")
        out(f"FIXTURE_ARTIFACT={written}")

    failed = checks.count(False)
    out(f"{'ALL LEGS PASS' if failed == 0 else f'{failed} FAILED'}  {sum(checks)}/{len(checks)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
