#!/usr/bin/env python3
"""Author `envelope.json` — the fill-ins `envelope/launch.js#loadFillIns` reads at every
caged spawn. ONE producer, TWO destinations, and the second is what makes the first reach
a goal that is already alive.

  --plan-artifacts <dir>   `<plan-artifacts>/envelope.json`, the PLAN-side artifact the bound
                           commit carries and `path_b.bound_envelope_fillins` reads at birth.
  --goal-dir <dir>         `<goal-dir>/envelope.json`, the BORN-goal artifact `loadFillIns`
                           reads. Compile-checked first, then landed by the same
                           exclusive-create writer the birth uses.

THE GAP `--plan-artifacts` CLOSED. `path_b.bound_envelope_fillins` reads that file from the
bound commit (`git show`, never the working tree). Birth-envelope (`_land_envelope`) is the
consumer of that tree object. Nothing in planning wrote it, so every birth copied nothing and
`compilePlanning` hardcoded `credentialNames: []`.

THE GAP `--goal-dir` CLOSES (`ignite-engine-loop` M1 Observable B; register filing
`G-leader-0831-1620`). The birth-side landing only fires DURING a birth, and only when the
bound commit already carries the plan artifact. A goal born before that fix deployed, or from
an approved plan whose artifacts carry no `envelope.json` — the common case, and the case of
`ignite-engine-loop` itself — gets no file and boots under `compilePlanning`, every declared
write root read-only, with nothing but one stderr line to say so. There was no production
writer for that goal at all, and the remedy in reach was a hand-written file: a console
repair, one goal at a time, that leaves the next goal exactly as stuck. This is that writer.

⚠ IT IS A PRODUCER, NOT AN EDITOR. `write_envelope_if_absent` is `O_CREAT|O_EXCL`: an
existing `envelope.json` is REPORTED and never replaced, here as at birth. Changing a live
goal's grants is a re-birth or a deliberate removal, never a silent overwrite by a CLI that
was asked to create one.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "coord"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from records import atomic_write  # noqa: E402  (coord's one write door)
# The BORN-GOAL half of this producer reuses the birth's own gate and writer rather than
# growing a second copy of either: `compile_check_envelope` drives the real
# `envelope/compiler.js`, and `write_envelope_if_absent` is the `O_CREAT|O_EXCL` landing
# whose comment explains why it is not `tmp + rename`. `path_b` does not import this module,
# so the edge is one-way.
from failure import MaterializeFailure  # noqa: E402  (what the compile gate raises)
from path_b import compile_check_envelope, write_envelope_if_absent  # noqa: E402

# Must match `path_b.ENVELOPE_ARTIFACT_NAME` and `envelope/launch.js#FILL_IN_NAME`.
ENVELOPE_ARTIFACT_NAME = "envelope.json"

KNOWN_KEYS = ("namedRepos", "projectFolder", "credentialNames", "extraPaths")
CREDENTIAL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ACCESS = ("rw", "ro")


class PlanEnvelopeRefusal(Exception):
    """A fill-in object that would be written wrong. Refused before any byte lands."""

    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def envelope_artifact_path(plan_artifacts):
    return Path(plan_artifacts) / ENVELOPE_ARTIFACT_NAME


def _names(value, *, field):
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise PlanEnvelopeRefusal(
            "bad-fillins",
            f"{field} must be a JSON array of strings, not {type(value).__name__}",
        )
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PlanEnvelopeRefusal(
                "bad-fillins",
                f"{field} entries must be non-empty strings, got {item!r}",
            )
        out.append(item)
    return out


def _credential_names(value):
    """`credentialNames` entries are a bare env-var-name string (unchanged) OR the typed account
    shape `{"type": "gtools-account", "account": "<name>"}` (`d-credential-account-shape`,
    `d-ask17-credential-token-broker`, `d-hold5-wire-the-broker`) — a gtools OAuth account the
    admission-time broker check (`envelope/credentials.js#isAccountCredentialEntry`,
    `#resolveAccountCredentials`) resolves against `gtools/credentials/<account>/`, never `.env`.
    Kept in lockstep with that reader — the ONE other place this shape is interpreted — rather
    than a second, independently-evolving schema.
    """
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise PlanEnvelopeRefusal(
            "bad-fillins",
            f"credentialNames must be a JSON array, not {type(value).__name__}",
        )
    out = []
    seen_names = set()
    seen_accounts = set()
    for item in value:
        if isinstance(item, str):
            if not item.strip():
                raise PlanEnvelopeRefusal(
                    "bad-fillins",
                    f"credentialNames entries must be non-empty strings, got {item!r}",
                )
            if not CREDENTIAL_NAME_RE.match(item):
                raise PlanEnvelopeRefusal(
                    "bad-credential-name",
                    f"{item!r} is not an env-var name ([A-Za-z_][A-Za-z0-9_]*)",
                )
            if item in seen_names:
                raise PlanEnvelopeRefusal("bad-credential-name", f"{item} is duplicated")
            seen_names.add(item)
            out.append(item)
            continue
        if isinstance(item, dict) and item.get("type") == "gtools-account":
            account = item.get("account")
            if not isinstance(account, str) or not account.strip():
                raise PlanEnvelopeRefusal(
                    "bad-credential-name",
                    f"gtools-account entry needs a non-empty account, got {item!r}",
                )
            unknown = [k for k in item if k not in ("type", "account")]
            if unknown:
                raise PlanEnvelopeRefusal(
                    "bad-fillins",
                    f"credentialNames gtools-account entry has unknown keys {unknown}",
                )
            if account in seen_accounts:
                raise PlanEnvelopeRefusal("bad-credential-name", f"gtools-account:{account} is duplicated")
            seen_accounts.add(account)
            out.append({"type": "gtools-account", "account": account})
            continue
        raise PlanEnvelopeRefusal(
            "bad-fillins",
            "credentialNames entries must be a non-empty string or "
            f"{{'type':'gtools-account','account':<name>}}, got {item!r}",
        )
    return out


def _extra_paths(value):
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise PlanEnvelopeRefusal(
            "bad-fillins",
            f"extraPaths must be a JSON array, not {type(value).__name__}",
        )
    out = []
    for item in value:
        if not isinstance(item, dict) or not item.get("path"):
            raise PlanEnvelopeRefusal(
                "bad-fillins",
                "each extraPaths entry needs a non-empty path",
            )
        access = item.get("access")
        if access not in ACCESS:
            raise PlanEnvelopeRefusal(
                "bad-fillins",
                f"extraPaths access must be rw or ro, got {access!r}",
            )
        extra = {"path": str(item["path"]), "access": access}
        unknown = [k for k in item if k not in extra]
        if unknown:
            raise PlanEnvelopeRefusal(
                "bad-fillins",
                f"extraPaths entry has unknown keys {unknown}",
            )
        out.append(extra)
    return out


def build_fillins(raw=None, **fields):
    """Validate and return the object `compile()` / `consumeLaunch` read."""
    src = dict(raw or {})
    src.update({k: v for k, v in fields.items() if v is not None})
    unknown = [k for k in src if k not in KNOWN_KEYS]
    if unknown:
        raise PlanEnvelopeRefusal(
            "bad-fillins",
            f"unknown keys {unknown} — compile reads only {list(KNOWN_KEYS)}",
        )
    fill = {}
    names = _credential_names(src.get("credentialNames"))
    if names is not None:
        fill["credentialNames"] = names
    repos = _names(src.get("namedRepos"), field="namedRepos")
    if repos is not None:
        fill["namedRepos"] = repos
    if "projectFolder" in src:
        pf = src["projectFolder"]
        if pf is not None and not isinstance(pf, str):
            raise PlanEnvelopeRefusal(
                "bad-fillins",
                f"projectFolder must be a string or null, not {type(pf).__name__}",
            )
        fill["projectFolder"] = pf
    extras = _extra_paths(src.get("extraPaths"))
    if extras is not None:
        fill["extraPaths"] = extras
    if not fill:
        raise PlanEnvelopeRefusal(
            "empty-fillins",
            "envelope.json would carry no namedRepos/projectFolder/credentialNames/extraPaths",
        )
    return fill


def write_plan_envelope(plan_artifacts, fillins):
    """Write `<plan_artifacts>/envelope.json` atomically. Returns the path written."""
    body = build_fillins(fillins)
    dest = envelope_artifact_path(plan_artifacts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(dest, json.dumps(body, indent=2, sort_keys=True) + "\n")
    return dest


def spawning_compiler():
    """The `envelope/compiler.js` THE DAEMON RUNS — which is the one that will read the file.

    ⚠ NOT NECESSARILY THIS TREE'S. Under the D6 deploy model the daemon boots from a detached
    worktree (`ExecStart=…/rbtv-deploy/ignite/runtime/index.js`) while a human runs this module
    from the live source tree, and the two drift: measured 2026-08-31, the deployed copy was four
    days behind the repo on `compiler.js`, `launch.js`, `spawn.js` and `path_b.py`, and did not
    carry `plan_envelope.py` at all. Gating a landing on the local copy therefore checks a compiler
    that will never see the file.

    ⚠ ONE CONVENTION FOR "THE TREE THE DAEMON RUNS", NOT A SECOND ONE INVENTED HERE:
    `RBTV_IGNITE_DEPLOY`, else `$XDG_STATE_HOME/rbtv-deploy` — the same resolution
    `operator/daemon-operator/tool/rbtv-ignite-daemon` and `goal_cli.py#_daemon_counters_file`
    already use for the same question.

    Falls back to THIS tree's compiler when no deploy tree carries one (a fresh install, a fixture,
    a probe workspace) — there, this tree is the tree that runs.
    """
    deploy = os.environ.get("RBTV_IGNITE_DEPLOY")
    if not deploy:
        state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
        deploy = str(Path(state) / "rbtv-deploy")
    candidate = Path(deploy) / "ignite" / "envelope" / "compiler.js"
    return candidate if candidate.is_file() else COMPILER_JS


def land_goal_envelope(goal_dir, fillins, compiler_js=None):
    """Compile-check `fillins` against the REAL compiler, then land `<goal_dir>/envelope.json`.

    ⚠ NOTHING IS RE-IMPLEMENTED HERE. The validator is `build_fillins` above (the one grammar),
    the compile gate is `path_b.compile_check_envelope` (the one gate, driving the real
    `envelope/compiler.js` through node exactly as the birth does), and the writer is
    `path_b.write_envelope_if_absent` (the one exclusive-create landing). A second spelling of
    any of the three is how a goal's envelope and its birth's envelope come to disagree.

    ⚠ COMPILE-CHECK BEFORE LANDING, never after, AND AGAINST THE COMPILER THAT WILL READ THE
    FILE — `spawning_compiler()`, not necessarily this tree's. A refusing `envelope.json` on disk
    is strictly worse than none: `loadFillIns` finds it, `compile()` refuses, and the seat does not
    spawn at all, where an ABSENT file merely falls back to `compilePlanning`. Both halves were
    measured on 2026-08-31: gating on a repo copy that carried a new carve rule landed a file the
    DEPLOYED compiler refused `{kind:conflict}`, which would have made every caged seat of that
    goal unspawnable. The birth makes the same call in the same order, and its own default already
    resolves to the daemon's tree because the birth runs inside it.

    Returns `(dest, verdict, status, compiler)`; `status` is `"written"` or `"already-present"`.
    """
    goal_dir = Path(goal_dir).resolve()
    if not goal_dir.is_dir():
        raise PlanEnvelopeRefusal("no-such-goal", f"{goal_dir} is not a directory")
    body = build_fillins(fillins)
    # `goalId`, the goal folder's `name` and the folder itself are ONE string by construction:
    # family 1 bakes `{workspace}/.rbtv/goals/{goal}`, so a goal whose id differed from its
    # folder name would compile a path that does not exist. Deriving all three from the folder
    # is what keeps this producer from being able to spell a goal that cannot boot.
    compiler = Path(compiler_js) if compiler_js else spawning_compiler()
    verdict = compile_check_envelope(
        goals_root=goal_dir.parent,
        goal_id=goal_dir.name,
        fillins=body,
        name=goal_dir.name,
        compiler_js=compiler,
    )
    status = write_envelope_if_absent(goal_dir, body)
    return envelope_artifact_path(goal_dir), verdict, status, compiler


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="plan-envelope",
        description="Write envelope.json — the cage fill-ins. --plan-artifacts writes the PLAN-side "
                    "artifact the bound commit carries (run by a planning seat before the bound "
                    "commit is taken); --goal-dir compile-checks and lands the BORN goal's own file "
                    "(run for a goal that is already alive and has none).",
    )
    dest = ap.add_mutually_exclusive_group(required=True)
    dest.add_argument(
        "--plan-artifacts",
        help="directory the bound commit will include; envelope.json lands at its root",
    )
    dest.add_argument(
        "--goal-dir",
        help="a born goal's folder; envelope.json is compile-checked and landed at its root, "
             "and an existing one is reported rather than replaced",
    )
    ap.add_argument(
        "--compiler",
        default=None,
        help="path to the envelope/compiler.js that will READ the landed file. Default: the tree "
             "the daemon runs (RBTV_IGNITE_DEPLOY, else $XDG_STATE_HOME/rbtv-deploy), else this "
             "tree's. Only pass it to gate against a tree neither of those names",
    )
    ap.add_argument(
        "--extra-path",
        action="append",
        default=[],
        dest="extra_paths",
        metavar="PATH:rw|ro",
        help="a declared extraPaths grant, workspace-relative or absolute (repeatable). "
             "The access suffix is required — an unstated access is a grant nobody can audit",
    )
    ap.add_argument(
        "--credential-name",
        action="append",
        default=[],
        dest="credential_names",
        help="env name to inject into the cage (repeatable). First consumer: ELEVENLABS_API_KEY",
    )
    ap.add_argument(
        "--from-json",
        default=None,
        help="path to a JSON object of fill-ins; --credential-name values are appended",
    )
    ap.add_argument("--json", action="store_true", help="print the written object")
    args = ap.parse_args(argv)

    raw = {}
    if args.from_json:
        try:
            loaded = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"ok": False, "refusal": {"code": "bad-fillins", "detail": str(exc)}}))
            return 2
        if not isinstance(loaded, dict):
            print(json.dumps({
                "ok": False,
                "refusal": {"code": "bad-fillins", "detail": "--from-json must be a JSON object"},
            }))
            return 2
        raw.update(loaded)
    if args.credential_names:
        raw["credentialNames"] = list(raw.get("credentialNames") or []) + list(args.credential_names)
    for spec in args.extra_paths:
        target, _, access = spec.rpartition(":")
        if not target or access not in ACCESS:
            print(json.dumps({"ok": False, "refusal": {
                "code": "bad-fillins",
                "detail": f"--extra-path takes PATH:rw or PATH:ro, got {spec!r}",
            }}, indent=2))
            return 2
        raw["extraPaths"] = list(raw.get("extraPaths") or []) + [{"path": target, "access": access}]

    if args.plan_artifacts:
        try:
            dest = write_plan_envelope(args.plan_artifacts, raw)
        except PlanEnvelopeRefusal as exc:
            print(json.dumps({"ok": False, "refusal": {"code": exc.code, "detail": exc.detail}}, indent=2))
            return 2
        if args.json:
            print(dest.read_text(encoding="utf-8"), end="")
        else:
            print(f"plan-envelope written: {dest}")
        return 0

    try:
        dest, verdict, status, compiler = land_goal_envelope(args.goal_dir, raw, args.compiler)
    except PlanEnvelopeRefusal as exc:
        print(json.dumps({"ok": False, "refusal": {"code": exc.code, "detail": exc.detail}}, indent=2))
        return 2
    except MaterializeFailure as exc:
        # The compile gate refused, so NOTHING was written — the goal keeps its (absent) envelope
        # and its `compilePlanning` fallback rather than gaining one that refuses every spawn.
        print(json.dumps({"ok": False, "refusal": {"code": exc.code, "detail": str(exc)}}, indent=2))
        return 2
    if args.json:
        print(dest.read_text(encoding="utf-8"), end="")
    else:
        rw = [b["path"] for b in verdict.get("binds", []) if b.get("access") == "rw"]
        print(f"goal-envelope {status}: {dest}")
        # The compiler is NAMED, always. It is the one fact that decides whether this landing is
        # safe, and it is not derivable from the exit code.
        print(f"compile ok against {compiler}: {len(verdict.get('binds', []))} binds, {len(rw)} read-write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
