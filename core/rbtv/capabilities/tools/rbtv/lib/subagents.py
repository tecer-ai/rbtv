"""An agent a component ships, added to a target with `rbtv add`: it is written as a
harness-native sub-agent, for the harnesses a model and an effort were given
for. This file owns those values: the `--on HARNESS:MODEL:EFFORT` flag, where a
record keeps them, and what a result says about them.
"""
from __future__ import annotations

from pathlib import Path

from discovery import Refuse, file_rows

from .constants import HARNESSES
from .content import sub_agent_settings
from .recovery import shell_quote
from .selection import iter_catalog_parts

ON_FORM = "HARNESS:MODEL:EFFORT"


def _refuse(code: str, message: str, next_cmd: str) -> Refuse:
    exc = Refuse(code, message)
    exc.next = next_cmd
    return exc


def named_agents(catalog: dict, keys: set[str]) -> list[dict]:
    """The catalog rows of the agents among these file ids."""
    return [row for row in iter_catalog_parts(catalog)
            if row["key"] in keys and row["method"] == "agent"]


def parse_on(raw: list[str]) -> dict[str, tuple[str, str]]:
    """`--on` values as harness -> (model, effort); one value per harness."""
    out: dict[str, tuple[str, str]] = {}
    for value in raw:
        fields = value.split(":")
        if len(fields) != 3 or not all(fields):
            raise _refuse("usage", f"--on {value!r} is not {ON_FORM}", "rbtv add -h")
        harness, model, effort = fields
        if harness not in HARNESSES:
            raise _refuse("usage", f"--on {value!r} names no harness; known: "
                          + ", ".join(HARNESSES), "rbtv add -h")
        if harness in out:
            raise _refuse("usage", f"--on names {harness} more than once; give one "
                          "value per harness", "rbtv add -h")
        out[harness] = (model, effort)
    return out


def values_for(on: list[str], named: list[dict], receiving: list[str],
               target: Path, *, known: dict, check, model_id,
               configure_cmd: str) -> dict[str, dict]:
    """The checked `--on` values for the agents a command names, by file id then
    harness: {model, model_id, effort}. `known` is `cast list`, `check` the
    check an rbtv agent's values get, `model_id` the harness's own id for a
    model. `configure_cmd` is the command that changes what the target receives."""
    names = ", ".join(row["file_id"] for row in named)
    if on and not named:
        raise _refuse("on-without-agent",
                      "--on gives a model and an effort to an agent a component "
                      "ships, and no such agent is among the names. Remove --on, "
                      "or name the agent",
                      "rbtv list --type agent --target " + shell_quote(target))
    if named and not on:
        first = named[0]["file_id"]
        raise _refuse("on-required",
                      f"{names}: an agent a component ships. Added with `rbtv add` it is "
                      "written as a harness-native sub-agent, which needs a model "
                      f"and an effort for each harness: give --on {ON_FORM}, once "
                      "per harness. To place it as an rbtv agent instead, run "
                      f"`rbtv agent add {first} --harness HARNESS --model MODEL "
                      "--effort EFFORT`", "cast list")
    given = parse_on(on)
    outside = [h for h in given if h not in receiving]
    if outside:
        raise _refuse("on-harness-not-received",
                      f"--on names {', '.join(outside)}, which this target does not "
                      f"receive. It receives: {', '.join(receiving)}. A harness-native "
                      "sub-agent is written only for a harness the target receives",
                      configure_cmd)
    values = {}
    for harness, (model, effort) in given.items():
        launch = check(harness, model, effort, known)
        values[harness] = {"model": launch["model"], "effort": launch["effort"],
                           "model_id": model_id(harness, launch["model"], target)}
    return {row["key"]: dict(values) for row in named}


def recorded(state: dict) -> dict[str, dict]:
    """The sub-agent values a record holds, by file id then harness."""
    return {f"{cid}#{pid}": file["sub_agent"]
            for cid, rec in (state.get("components") or {}).items()
            for pid, file in (rec.get("units") or {}).items()
            if isinstance(file, dict) and file.get("sub_agent")}


def installed_lines(values: dict[str, dict]) -> list[str]:
    """`Sub-agent ID: harness (model, effort); ...`, one line per recorded agent."""
    return [f"Sub-agent {key}: " + "; ".join(f"{h} ({text(v)})" for h, v in by.items())
            for key, by in sorted(values.items())]


def add_command(name: str, harness: str, target: Path) -> str:
    """The command that adds one agent as a sub-agent for one harness."""
    return (f"rbtv add {name} --on {harness}:MODEL:EFFORT --target "
            + shell_quote(target))


def describe(named: list[dict], given: dict[str, dict], before: dict[str, dict],
             receiving: list[str], catalog: dict, target: Path) -> list[dict]:
    """What a result says of each agent added as a sub-agent: the harnesses it
    is written for, with the values before when they changed; the receiving
    harnesses left out, each with the command that adds it; the agent's own
    files and packs, which are not applied; the values a file cannot carry."""
    out = []
    for row in named:
        key, name = row["key"], row["file_id"]
        was = before.get(key) or {}
        now = {h: v for h, v in {**was, **(given.get(key) or {})}.items()
               if h in receiving}
        data = next(r["data"] for r in file_rows(catalog[row["component"]])
                    if r["id"] == name)
        left_out = [h for h in receiving if h not in now]
        out.append({
            "id": key, "name": name,
            "harnesses": {h: {**now[h], "was": was.get(h) if was.get(h) != now[h] else None,
                              "not_applied": sub_agent_settings(h, now[h])[1]}
                          for h in receiving if h in now},
            "not_written_for": left_out,
            "add_commands": {h: add_command(name, h, target) for h in left_out},
            "files_not_applied": list(data.get("units") or []),
            "packs_not_applied": list(data.get("packs") or [])})
    return out


def text(values: dict) -> str:
    """One harness's values as a result prints them."""
    return f"{values['model']}, effort {values['effort']}"


def missing_note(name: str, written: list[str], harness: str, command: str) -> str:
    """Why a receiving harness has no sub-agent file, and the command that adds it."""
    have = f" for {' and '.join(written)}" if written else ""
    return (f"{name} is a harness-native sub-agent{have}, not for {harness}. rbtv "
            "cannot add it by itself: a model and an effort are needed. "
            f"Add it with: {command}")


def rows(report: list[dict]) -> list[tuple[str, str]]:
    """The summary rows of a result: one per agent, one per receiving harness."""
    out: list[tuple[str, str]] = []
    for agent in report:
        out.append(("Sub-agent", f"{agent['name']} (harness-native sub-agent)"))
        for harness, values in agent["harnesses"].items():
            was = f" (was {text(values['was'])})" if values["was"] else ""
            out.append((f"  {harness}", text(values) + was))
        out += [(f"  {harness}", "not written") for harness in agent["not_written_for"]]
    return out


def notes(report: list[dict]) -> list[str]:
    """The notes of a result, in the order a reader needs them."""
    out: list[str] = []
    for agent in report:
        name = agent["name"]
        out += [missing_note(name, list(agent["harnesses"]), harness, command)
                for harness, command in agent["add_commands"].items()]
        own = ([f"pack {pack}" for pack in agent["packs_not_applied"]]
               + [f"file {file}" for file in agent["files_not_applied"]])
        if own:
            out.append(f"{name}'s own files and packs were not applied: "
                       + ", ".join(own) + ". A harness-native sub-agent sees what "
                       "its target has; add them with `rbtv add`.")
        for harness, values in agent["harnesses"].items():
            out += [f"{name} for {harness}: {gap['setting']} {gap['value']} was "
                    f"recorded and not applied ({gap['reason']})."
                    for gap in values["not_applied"]]
    return out


def missing_for(state: dict, added: list[str], receiving: list[str],
                target: Path) -> list[dict]:
    """After a harness joined a target: each recorded sub-agent that is not
    written for it, with the command that adds it. Nothing is generated for a
    new harness by itself."""
    out = []
    for key, values in sorted(recorded(state).items()):
        name = key.split("#", 1)[1]
        written = [h for h in receiving if h in values]
        out += [{"id": key, "name": name, "written_for": written, "harness": harness,
                 "command": add_command(name, harness, target)}
                for harness in added if written and harness not in values]
    return out


def unset_note(key: str, target: str) -> str:
    """A chosen agent that no receiving harness has a model and an effort for."""
    name = key.split("#", 1)[1]
    return (f"{key} is chosen and has no model and effort for a receiving harness, "
            "so no harness-native sub-agent file is written for it. Add them with: "
            f"rbtv add {name} --on {ON_FORM} --target {shell_quote(target)}")
