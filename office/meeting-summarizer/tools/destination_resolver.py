#!/usr/bin/env python3
"""Destination resolution for the transcript summarizer.

The mechanism goal.md clause 6 assumes and the workspace did not have: a meeting
is mapped to a filing destination by READING owner configuration, never by a map
written into this file. Adding a business entity is an edit to configuration.

This module knows three things and no more:

  * how to turn a CONFIG KEY into the file that key names (`config_path`),
  * how to evaluate the declarative predicates a route may carry,
  * how to render a route's path template in the configured timezone.

It knows no repository name, no path segment and no participant. Every one of
those is data it reads. `grep` over this tree for the destination-name surface is
the check that keeps it that way, and it is the point of the design.

Clause 7 is why `unroutable` is a TYPED ANSWER returned with exit 0 rather than
an exception: a caller that catches an exception can swallow it into a default,
and a default is the one outcome the contract forbids. A route carrying no
predicate at all is REFUSED AT LOAD for the same reason — it would be a
catch-all, which is a default wearing configuration's clothes.

Routing NEVER keys on the Google account a meeting was held in (owner ruling
r-route-by-content-not-account, 2026-09-27): the owner holds clinical, business
and personal meetings on one account. A route is chosen in TWO passes. Pass one
evaluates each route's declarative `match` predicates — deterministic facts such
as a clinician's name among the participants — and always runs first, so a fact
can never be overruled by a reading. Pass two applies only when pass one found
nothing: a route may declare `content`, a plain description of what its meetings
are about, and the per-meeting job asks a model which declared description the
meeting's content fits (`content_routes`). The model's pick arrives on the job as
`content-entity`; "unsure" or no pick at all stays `unroutable` and is ASKED.

A route answers with a REPO. Where inside that repo the file lands is the
destination repo's own rule (owner ruling 2026-08-31,
`r-routing-destinations-and-delegation` item 2: "the repo's claude.mds already do
the routing"), so `path-template` is OPTIONAL: a route without one resolves to
`placement: "delegated"` and this resolver invents no path. A route WITH one
resolves to a rendered repo-relative path — the form the contract fixes for the
dated clinical destination.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# --------------------------------------------------------------- identity
# The component this resolver belongs to. Not a destination: the module and
# component names are this code's own address, and they are what turns a config
# key into a file. The config-module home is the location the `destination-repo-set`
# seam's `config-key` $def names in so many words.
CONFIG_ROOT_ENV = "MEETING_SUMMARIZER_CONFIG_ROOT"

# The two config KEYS this resolver reads. Keys, never paths.
ROUTING_KEY = "destination-routing"  # the declared source: the owner's route table
REPOS_KEY = "destination-repos"  # the seam-declared repo set (`destination-repo-set`)

# The vocabulary the seam set defines for a config key.
CONFIG_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9/-]*$")

# A `{name}` slot in a route's path template.
TEMPLATE_SLOT_RE = re.compile(r"\{([a-z0-9_-]+)\}")

# The predicate kinds a route may declare. This tuple is the MECHANISM; the
# values a route puts under each kind are owner configuration.
# There is deliberately NO account predicate: owner ruling
# r-route-by-content-not-account (2026-09-27) — the owner holds clinical, business
# and personal meetings on one Google account, so an account can never decide.
PREDICATE_KINDS = ("participants-any", "title-matches")

EXIT_OK = 0
EXIT_REFUSED = 2  # could not run — same convention as validate_seams.py


class Refused(Exception):
    """The resolver could not run. Never a routing answer, never a default."""


# --------------------------------------------------------------- plumbing
def _refuse(what: str, why: str, fix: str) -> None:
    raise Refused(f"{what}: {why}\n  fix: {fix}")


def _fold(text: str) -> str:
    """Casefold and strip combining marks, so 'Ines' matches 'Ines' accented."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold().strip()


def config_root(override: str | Path | None = None) -> Path:
    """The config-module home this component's keys resolve under.

    No workspace-relative default: this capability carries no vault path of its
    own (it moved into rbtv, reusable by any agent). The caller names its config
    home explicitly, or sets `MEETING_SUMMARIZER_CONFIG_ROOT` — the agent home's
    settings folder, in the ignite-0.2 design that reaches this resolver.
    """
    if override:
        return Path(override).expanduser()
    env = os.environ.get(CONFIG_ROOT_ENV)
    if env:
        return Path(env).expanduser()
    _refuse(
        "config-module home",
        "neither an explicit path nor the environment variable is set",
        f"pass the config-module home explicitly, or set {CONFIG_ROOT_ENV}",
    )
    raise AssertionError("unreachable")


def config_path(key: str, override: str | Path | None = None) -> Path:
    """THE binding: a config KEY -> the file it names.

    The rule is the component's live one, read off `channel_protocol.resolve_store`
    rather than invented here: a key `<group>/<leaf>` lives in `<group>.json` under
    the config-module home, at object key `<leaf>`. A FLAT key `<name>` — the form
    `destination-repos` and `glossary-path` take, which that helper does not
    resolve — lives in `<name>.json` and IS the whole file, matching the
    `forge.json` / `interactive-exposes.json` precedent at a component root.

    This is the only place a location is computed, and it is computed from a key.
    """
    if not CONFIG_KEY_RE.match(key) or ".." in key.split("/"):
        _refuse("config-key", f"{key!r} is not a config key", "use the key the seam declares")
    group, _, _leaf = key.partition("/")
    return config_root(override) / f"{group}.json"


def config_datum(key: str, override: str | Path | None = None) -> dict:
    """The datum a config key names, for either key form."""
    path = config_path(key, override)
    group, _, leaf = key.partition("/")
    if not path.is_file():
        _refuse(
            f"config {key}",
            f"no file for this key at {path}",
            f"create the declared source for key '{key}' under the config-module home",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _refuse(f"config {key}", f"unreadable at {path}: {exc}", "repair the file")
    if leaf:
        if not isinstance(value, dict) or leaf not in value:
            _refuse(f"config {key}", f"{path} carries no '{leaf}' entry", f"add '{leaf}' to {path.name}")
        value = value[leaf]
    if not isinstance(value, dict):
        _refuse(f"config {key}", f"the datum at {key} is not an object", "the datum is a JSON object")
    return value


# --------------------------------------------------------------- the sources
def load_repo_names(override=None) -> set[str]:
    """Repo names from the `destination-repos` datum (`destination-repo-set` seam)."""
    data = config_datum(REPOS_KEY, override)
    repos = data.get("repos")
    if not isinstance(repos, list) or not repos:
        _refuse(f"config {REPOS_KEY}", "'repos' is missing or empty", "declare at least one repo")
    return {entry["name"] for entry in repos if isinstance(entry, dict) and "name" in entry}


def load_routing(override=None) -> dict:
    """The declared source: the owner's route table, validated as a MECHANISM.

    Validated here: that every route is well-formed, carries at least one
    predicate, and can actually be reached. NOT validated here: whether the
    owner's routing intent is right — that is the owner's to state, and this code
    never supplies a value for it.
    """
    key_path = config_path(ROUTING_KEY, override)
    data = config_datum(ROUTING_KEY, override)

    declared_key = data.get("config-key")
    if declared_key != ROUTING_KEY:
        _refuse(
            f"config {ROUTING_KEY}",
            f"'config-key' reads {declared_key!r}, expected {ROUTING_KEY!r}",
            "a config datum names its own key",
        )

    tzname = data.get("timezone")
    if not tzname:
        _refuse(
            f"config {ROUTING_KEY}",
            "'timezone' is absent",
            "declare the timezone the date slots are computed in (owner ruling 2026-08-28)",
        )
    try:
        tzinfo = ZoneInfo(tzname)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        _refuse(f"config {ROUTING_KEY}", f"timezone {tzname!r} is unknown: {exc}", "use an IANA name")

    routes = data.get("routes")
    if not isinstance(routes, list):
        _refuse(f"config {ROUTING_KEY}", "'routes' is missing or not a list", "declare a route list")

    known_repos = load_repo_names(override)
    for index, route in enumerate(routes):
        _validate_route(route, index, known_repos)
    _refuse_unreachable_routes(routes)

    return {"timezone": tzname, "tzinfo": tzinfo, "routes": routes, "source": key_path}


def _validate_route(route: dict, index: int, known_repos: set[str]) -> None:
    where = f"route[{index}]"
    if not isinstance(route, dict):
        _refuse(f"config {ROUTING_KEY}", f"{where} is not an object", "each route is an object")

    for field in ("entity", "destination"):
        if field not in route:
            _refuse(f"config {ROUTING_KEY}", f"{where} has no '{field}'", f"add '{field}'")

    match = route.setdefault("match", {})
    if not isinstance(match, dict):
        _refuse(f"config {ROUTING_KEY}", f"{where}.match is not an object", "use predicate kinds")

    unknown = sorted(set(match) - set(PREDICATE_KINDS))
    if unknown:
        _refuse(
            f"config {ROUTING_KEY}",
            f"{where}.match declares unknown predicate(s) {unknown}",
            f"the predicate kinds are {list(PREDICATE_KINDS)}",
        )

    declared = {kind: value for kind, value in match.items() if value}
    content = route.get("content")
    if content is not None and not (isinstance(content, str) and content.strip()):
        _refuse(f"config {ROUTING_KEY}", f"{where}.content is empty",
                "describe in plain words what this route's meetings are about, or drop it")
    if not declared and not content:
        # A route that matches everything is a default, and clause 7 forbids one.
        _refuse(
            f"config {ROUTING_KEY}",
            f"{where} declares neither a match predicate nor a content description — it "
            "would match every meeting",
            "a catch-all route is a default; clause 7 forbids defaulting. Give it one",
        )

    destination = route["destination"]
    if not isinstance(destination, dict):
        _refuse(f"config {ROUTING_KEY}", f"{where}.destination is not an object", "use a repo")
    if not destination.get("repo"):
        _refuse(f"config {ROUTING_KEY}", f"{where}.destination has no 'repo'", "add 'repo'")

    # `path-template` is OPTIONAL: absent means in-repo placement is the
    # destination repo's own rule, and this resolver returns no path at all.
    if "path-template" in destination and not isinstance(destination["path-template"], str):
        _refuse(
            f"config {ROUTING_KEY}",
            f"{where}.destination.path-template is not a string",
            "give a template string, or drop the field to delegate placement to the repo",
        )
    if destination.get("path-template") == "":
        _refuse(
            f"config {ROUTING_KEY}",
            f"{where}.destination.path-template is empty",
            "an empty template is not delegation — drop the field to delegate",
        )

    repo = destination["repo"]
    if repo not in known_repos:
        _refuse(
            f"config {ROUTING_KEY}",
            f"{where}.destination.repo {repo!r} is not in the '{REPOS_KEY}' datum",
            f"declare {repo!r} in the '{REPOS_KEY}' config datum, or fix the name",
        )


def _refuse_unreachable_routes(routes: list) -> None:
    """Refuse a route an earlier route can never let through.

    Routes are FIRST-MATCH-WINS, so a broad route placed above a narrow one
    silently swallows the narrow one's meetings. That is not a style problem: the
    narrow routes here are the ones carrying clinical traffic, and the broad one
    is the catch for everything broader. Reordering the table by
    hand would file private material into the wrong destination with no error
    anywhere. The shadowing is decidable from the predicates alone, so it is
    refused at load rather than discovered downstream.

    Earlier route E shadows later route L when E declares a subset of L's
    predicate kinds and, for each kind it does declare, L's values are a subset of
    E's: every meeting L would match, E matched first.
    """
    for later_index, later in enumerate(routes):
        for earlier_index, earlier in enumerate(routes[:later_index]):
            # A content-only route has no predicate and is never in pass one.
            if not any(earlier["match"].values()) or not any(later["match"].values()):
                continue
            if _shadows(earlier["match"], later["match"]):
                _refuse(
                    f"config {ROUTING_KEY}",
                    f"route[{later_index}] '{later['entity']}' can never match: "
                    f"route[{earlier_index}] '{earlier['entity']}' is broader and comes first",
                    "put the more specific route ABOVE the broader one, "
                    "or narrow the broader route's predicates",
                )


def _shadows(earlier: dict, later: dict) -> bool:
    earlier_kinds = {kind for kind, value in earlier.items() if value}
    later_kinds = {kind for kind, value in later.items() if value}
    if not earlier_kinds <= later_kinds:
        return False
    for kind in earlier_kinds:
        if not {_fold(v) for v in later[kind]} <= {_fold(v) for v in earlier[kind]}:
            return False
    return True


# --------------------------------------------------------------- signals
def meeting_signals(job: dict) -> dict:
    """Reduce a `meeting-key-and-source-set` instance to the signals a route sees.

    A meeting's START is the EARLIEST start across its paired sources: the same
    meeting is recorded twice (a Meet record and a Tactiq record start minutes
    apart), and the earliest is the one that is the meeting's own start rather
    than a transcriber's join. Disclosed as a judgment call, not a contract term.
    """
    sources = job.get("source-set")
    if not isinstance(sources, list) or not sources:
        _refuse("job", "'source-set' is missing or empty", "pass a meeting-key-and-source-set instance")

    stamped = []
    for record in sources:
        raw = record.get("start-time")
        if not raw:
            _refuse("job", "a source record has no 'start-time'", "start-time is required by the seam")
        try:
            stamped.append((datetime.fromisoformat(raw), record))
        except ValueError as exc:
            _refuse("job", f"start-time {raw!r} is not RFC 3339: {exc}", "emit an offset-carrying stamp")
    if any(stamp.tzinfo is None for stamp, _ in stamped):
        _refuse("job", "a start-time carries no UTC offset", "the seam requires an offset")

    earliest_start = min(stamp for stamp, _ in stamped)

    titles = [record.get("title") or "" for record in sources]
    participants: list[str] = []
    for record in sources:
        for name in record.get("participants") or []:
            if name not in participants:
                participants.append(name)

    return {
        "meeting-key": job.get("meeting-key"),
        "content-entity": job.get("content-entity"),
        "start": earliest_start,
        "title": next((title for title in titles if title), ""),
        "participants": participants,
    }


def _matches(route: dict, signals: dict) -> bool:
    """A route matches when every predicate it DECLARES matches (absent kinds are
    not evaluated); within one kind, any listed value matching is enough."""
    match = route["match"]

    wanted = match.get("participants-any")
    if wanted:
        # SUBSTRING, not equality. A participant reaches this code as the display
        # name its source happened to carry, and those are unstable — the same
        # person appears with and without a middle name, with and without accents,
        # spelled as the transcriber heard them. Equality would fail in the one
        # direction that matters: a route keyed on a person would silently stop
        # matching and the meeting would fall through to a broader route below it.
        # A configured value is therefore a distinguishing FRAGMENT of a name
        # (a surname), and picking one specific enough is the owner's to do.
        present = [_fold(name) for name in signals["participants"]]
        if not any(_fold(name) in display for name in wanted for display in present):
            return False

    patterns = match.get("title-matches")
    if patterns:
        title = signals["title"]
        if not any(re.search(pattern, title, re.IGNORECASE) for pattern in patterns):
            return False

    return True


# --------------------------------------------------------------- rendering
def render_template(template: str, route: dict, signals: dict, tzinfo: ZoneInfo) -> str:
    """Render a route's path template. Every slot must resolve; an unresolved slot
    is a REFUSAL, never a guessed path."""
    local_start = signals["start"].astimezone(tzinfo)
    slots = {
        "year": local_start.strftime("%Y"),
        "date": local_start.strftime("%Y-%m-%d"),
        "meeting-key": signals["meeting-key"] or "",
    }
    slots.update({str(k): str(v) for k, v in (route.get("vars") or {}).items()})

    missing = sorted({name for name in TEMPLATE_SLOT_RE.findall(template) if name not in slots})
    if missing:
        _refuse(
            "template",
            f"route '{route['entity']}' leaves slot(s) {missing} unresolved",
            "declare them under the route's 'vars', or remove them from the template",
        )

    rendered = TEMPLATE_SLOT_RE.sub(lambda m: slots[m.group(1)], template)

    # The seam's repo-file-ref: repo-relative POSIX path, never absolute.
    if rendered.startswith("/") or ".." in Path(rendered).parts:
        _refuse("template", f"rendered path {rendered!r} is not repo-relative", "use a relative template")
    return rendered


# --------------------------------------------------------------- the answer
def resolve(job: dict, override=None, routing: dict | None = None) -> dict:
    """Map one meeting to a destination, or to the typed value `unroutable`.

    Returns a `routed` or an `unroutable` record. The `unroutable` record is
    shaped as the `meeting-message-payload` seam's unroutable variant, so the
    caller forwards it rather than inventing a fallback.
    """
    routing = routing if routing is not None else load_routing(override)
    signals = meeting_signals(job)

    by_fact = [route for route in routing["routes"]
               if any(route["match"].values()) and _matches(route, signals)]
    by_content = [route for route in routing["routes"]
                  if route.get("content") and route["entity"] == signals["content-entity"]]
    for route in (by_fact or by_content)[:1]:
        destination = {"repo": route["destination"]["repo"]}
        template = route["destination"].get("path-template")
        if template:
            destination["path"] = render_template(template, route, signals, routing["tzinfo"])
            destination["placement"] = "template"
        else:
            # No path is invented here: the destination repo's own rules place it.
            destination["placement"] = "delegated"
        return {
            "kind": "routed",
            "meeting-key": signals["meeting-key"],
            "entity": route["entity"],
            "destination": destination,
        }

    return {
        "kind": "unroutable",
        "meeting-key": signals["meeting-key"],
        "signals": {"title": signals["title"], "participants": signals["participants"]},
    }


def content_routes(override=None, routing: dict | None = None) -> list[dict]:
    """The routes pass two may pick from: entity and its plain description."""
    routing = routing if routing is not None else load_routing(override)
    return [{"entity": route["entity"], "content": route["content"]}
            for route in routing["routes"] if route.get("content")]


# --------------------------------------------------------------- the walk
# A summary is identified by CONTENT, never by filename shape. Matching only the
# `-resumo.md` suffix leaves a hand-filed summary undiscoverable, and the
# downstream idempotence pre-check then re-summarizes work already done.
MARKER_RE = re.compile(r"^\s*(?:-\s*)?(?:meeting[-_]key|meeting key)\s*[:=]\s*(\S+)", re.IGNORECASE | re.MULTILINE)
SUMMARY_SUFFIXES = (".md", ".markdown")
WALK_SKIP_DIRS = frozenset({".git", "__pycache__", ".obsidian", "node_modules"})


def walk_summaries(root: Path) -> list[dict]:
    """Every filed summary under `root`, whatever it is called.

    Returns one record per markdown file, carrying the meeting key its marker
    declares when it has one. Filename shape is deliberately not a filter.
    """
    root = Path(root)
    if not root.is_dir():
        _refuse("walk", f"no such destination directory: {root}", "point --root at a directory")

    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if WALK_SKIP_DIRS & set(path.parts):
            continue
        if path.suffix.lower() not in SUMMARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        marker = MARKER_RE.search(text)
        found.append(
            {
                "path": path.relative_to(root).as_posix(),
                "meeting-key": marker.group(1) if marker else None,
                "suffix-conventional": path.name.endswith("-resumo.md"),
            }
        )
    return found


# --------------------------------------------------------------- CLI
def _read_job(path: str) -> dict:
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        _refuse("job", f"unreadable: {exc}", "pass a meeting-key-and-source-set JSON file, or - for stdin")
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="destination_resolver",
        description="Resolve a meeting to its filing destination by reading owner configuration.",
    )
    parser.add_argument(
        "--config-root",
        help=f"config-module home (default: ${CONFIG_ROOT_ENV})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    resolve_cmd = sub.add_parser("resolve", help="map one meeting to a destination or to unroutable")
    resolve_cmd.add_argument("--job", required=True, help="meeting-key-and-source-set JSON, or - for stdin")

    walk_cmd = sub.add_parser("walk", help="find filed summaries under a destination directory")
    walk_cmd.add_argument("--root", required=True, help="the destination directory to walk")

    sub.add_parser("keys", help="print the config keys this resolver reads and the files they name")

    args = parser.parse_args(argv)

    try:
        if args.command == "resolve":
            print(json.dumps(resolve(_read_job(args.job), args.config_root),
                             ensure_ascii=False, indent=2))
        elif args.command == "walk":
            print(json.dumps(walk_summaries(Path(args.root)), ensure_ascii=False, indent=2))
        else:
            print(
                json.dumps(
                    {key: str(config_path(key, args.config_root)) for key in (ROUTING_KEY, REPOS_KEY)},
                    indent=2,
                )
            )
    except Refused as exc:
        print(f"REFUSED {exc}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
