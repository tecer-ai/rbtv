"""The port fields of a component record: `type`, `serves`, `provides` and
`needs`. A record under `connectors/` without `type` is refused; a `needs`
entry no component `provides` is refused; the repository's own records are
accepted and the scan carries the four fields."""
from __future__ import annotations

import json
from pathlib import Path

from discovery import Refuse, scan_all, scan_tree

from lib.constants import REPO_ROOT

from .fixture import _module, _w


def _record(root: Path, module: str, comp: str, **fields: object) -> None:
    _module(root, module)
    record = {"description": f"The {comp} component", "dependencies": []}
    record.update(fields)
    _w(root / module / comp / f"{comp}.json", json.dumps(record))


def _refusal(fn) -> str:
    """The code of the refusal `fn` raises, or 'accepted'."""
    try:
        fn()
    except Refuse as exc:
        return exc.code
    return "accepted"


def _outcome(fn) -> tuple[str, str]:
    """The code and message of the refusal `fn` raises, or ('accepted', '')."""
    try:
        fn()
    except Refuse as exc:
        return exc.code, exc.message
    return "accepted", ""


def connector_records(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nCR — connector records: type, serves, provides and needs")

    # A connector record with no type.
    untyped = tmp / "cr-untyped"
    _record(untyped, "connectors", "nocat")
    check("CR-type-missing — a record under connectors/ without `type` is refused",
          _refusal(lambda: scan_tree(untyped, "repo")) == "type-missing",
          _refusal(lambda: scan_tree(untyped, "repo")))

    # The same record outside connectors/ needs no type.
    plain = tmp / "cr-plain"
    _record(plain, "fixmod", "plaincomp")
    check("CR-type-optional — a record outside connectors/ needs no `type`",
          _refusal(lambda: scan_tree(plain, "repo")) == "accepted",
          _refusal(lambda: scan_tree(plain, "repo")))

    # A need no component provides.
    unmet = tmp / "cr-unmet"
    _record(unmet, "connectors", "lonely", type="messaging", provides=["message.send"])
    _record(unmet, "core", "wanter", needs=["message.send", "agent.run"])
    no_mirror = tmp / "cr-unmet-mirror"
    no_mirror.mkdir()
    check("CR-needs-unmet — a `needs` entry no component provides is refused",
          _refusal(lambda: scan_all(no_mirror, unmet)) == "needs-unmet",
          _refusal(lambda: scan_all(no_mirror, unmet)))

    # The same need, met by a component of either tree.
    met = tmp / "cr-met"
    _record(met, "connectors", "talker", type="messaging",
            serves=["calendar"], provides=["message.send"])
    _record(met, "core", "wanter", needs=["message.send", "agent.run"])
    mirror = tmp / "cr-met-mirror"
    _record(mirror, "core", "runner", provides=["agent.run"])
    outcome = _refusal(lambda: scan_all(mirror, met))
    check("CR-needs-met — a need met by the repository or the mirror is accepted",
          outcome == "accepted", outcome)
    if outcome == "accepted":
        catalog, _shadowed = scan_all(mirror, met)
        talker = catalog["connectors/talker"]
        wanter = catalog["core/wanter"]
        check("CR-fields-carried — the scan carries type, serves, provides and needs",
              talker.get("type") == "messaging" and talker.get("serves") == ["calendar"]
              and talker.get("provides") == ["message.send"]
              and wanter.get("needs") == ["message.send", "agent.run"]
              and "type" not in wanter,
              json.dumps({k: talker.get(k) for k in ("type", "serves", "provides", "needs")}))

    # A mirror component written before the port fields replaces the shipped one
    # whole, so its missing `provides` unmeets a shipped need: the refusal keeps
    # the scan closed and names the mirror record and the field to backfill.
    old = tmp / "cr-mirror-old"
    _record(old, "core", "cast", provides=["agent.run"])
    _record(old, "core", "ignite", needs=["agent.run"])
    old_mirror = tmp / "cr-mirror-old-mirror"
    _record(old_mirror, "core", "cast")
    mirror_cast = old_mirror / "core" / "cast" / "cast.json"
    code, message = _outcome(lambda: scan_all(old_mirror, old))
    check("CR-mirror-needs — a mirror record without the shipped `provides` is refused as needs-unmet",
          code == "needs-unmet" and "core/ignite needs agent.run" in message, f"{code}: {message}")
    check("CR-mirror-backfill — that refusal names the mirror record and the `provides` to copy",
          str(mirror_cast) in message and "provides" in message
          and str(old / "core" / "cast" / "cast.json") in message, message)

    # The same for a mirror connector record without the shipped `type`.
    typed = tmp / "cr-mirror-typed"
    _record(typed, "connectors", "talker", type="messaging")
    typed_mirror = tmp / "cr-mirror-typed-mirror"
    _record(typed_mirror, "connectors", "talker")
    mirror_talker = typed_mirror / "connectors" / "talker" / "talker.json"
    code, message = _outcome(lambda: scan_all(typed_mirror, typed))
    check("CR-mirror-type — a mirror connector record without `type` is refused naming the mirror record and the shipped type",
          code == "type-missing" and str(mirror_talker) in message
          and str(typed / "connectors" / "talker" / "talker.json") in message and "'messaging'" in message,
          f"{code}: {message}")

    # A malformed operation name is refused by the schema.
    bad = tmp / "cr-badname"
    _record(bad, "connectors", "sloppy", type="messaging", provides=["Send"])
    check("CR-operation-form — an operation that is not <noun>.<verb> is refused",
          _refusal(lambda: scan_tree(bad, "repo")) == "record-invalid",
          _refusal(lambda: scan_tree(bad, "repo")))

    # The repository's own records, filled in.
    outcome = _refusal(lambda: scan_tree(REPO_ROOT, "repo"))
    check("CR-repo-accepted — every record of this repository is accepted",
          outcome == "accepted", outcome)
    if outcome == "accepted":
        repo = scan_tree(REPO_ROOT, "repo")
        connectors = sorted(cid for cid, comp in repo.items() if comp["module"] == "connectors")
        untyped_ids = [cid for cid in connectors if not repo[cid].get("type")]
        check("CR-repo-typed — every component under connectors/ names its type",
              connectors and not untyped_ids, ", ".join(untyped_ids) or "no connectors found")
        provided = {op for comp in repo.values() for op in comp.get("provides", [])}
        needing = {cid: comp["needs"] for cid, comp in repo.items() if comp.get("needs")}
        unmet_ops = {cid: [op for op in ops if op not in provided] for cid, ops in needing.items()}
        check("CR-repo-needs — every need of this repository is provided by a component",
              needing and not any(unmet_ops.values()), json.dumps(unmet_ops))
        check("CR-repo-cast-ignite — cast provides agent.run and ignite needs it",
              "agent.run" in repo.get("core/cast", {}).get("provides", [])
              and "agent.run" in repo.get("core/ignite", {}).get("needs", []),
              json.dumps({"cast": repo.get("core/cast", {}).get("provides"),
                          "ignite": repo.get("core/ignite", {}).get("needs")}))
