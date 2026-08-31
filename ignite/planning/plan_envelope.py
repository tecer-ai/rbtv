#!/usr/bin/env python3
"""Author `<plan-artifacts>/envelope.json` — the fill-ins Path-B copies at birth.

THE GAP THIS CLOSES. `path_b.bound_envelope_fillins` reads this file from the bound
commit (`git show`, never the working tree). Birth-envelope (`_land_envelope`) is the
consumer of that tree object. Nothing in planning wrote it, so every birth copied
nothing and `compilePlanning` hardcoded `credentialNames: []`. This module is the
producer. It does not land the file on the born goal and does not parse plan prose.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "coord"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from records import atomic_write  # noqa: E402  (coord's one write door)

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
    names = _names(value, field="credentialNames")
    if names is None:
        return None
    seen = set()
    for name in names:
        if not CREDENTIAL_NAME_RE.match(name):
            raise PlanEnvelopeRefusal(
                "bad-credential-name",
                f"{name!r} is not an env-var name ([A-Za-z_][A-Za-z0-9_]*)",
            )
        if name in seen:
            raise PlanEnvelopeRefusal("bad-credential-name", f"{name} is duplicated")
        seen.add(name)
    return names


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


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="plan-envelope",
        description="Write <plan-artifacts>/envelope.json for the bound commit Path-B reads. "
                    "Run by a planning-pipeline seat before the bound commit is taken.",
    )
    ap.add_argument(
        "--plan-artifacts",
        required=True,
        help="directory the bound commit will include; envelope.json lands at its root",
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


if __name__ == "__main__":
    sys.exit(main())
