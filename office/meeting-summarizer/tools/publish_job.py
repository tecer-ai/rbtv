#!/usr/bin/env python3
"""publish-job — file one meeting's summary and transcripts, and publish them.

The layer between "a summary exists" and "the owner can read it where they
already look". It owns six things and no others:

  * the PRE-CHECK — the destination is synced and searched for an existing
    summary BEFORE a summary is produced, so work is never done twice;
  * the DISCRIMINATOR — derived from the meeting's start time in the configured
    timezone and applied IDENTICALLY to the summary and to its transcripts, so
    two meetings of one client on one day cannot collide;
  * the AMENDMENT — a late second source rewrites the existing file in place,
    keyed on the meeting key, and never creates a second file;
  * PUBLICATION — commit and push inside the same cycle, in either of the two
    write regimes below;
  * the RESUMABLE JOURNAL — every stage is recorded as it completes, so a killed
    cycle resumes at the stage it died in;
  * the FULLY-PROCESSED record — written LAST, after the summary, the
    transcripts, publication and the filed-note have all landed.

It produces no summary text of its own: the text arrives from the caller's
`summarize` callable (the per-meeting job in the live wiring, a fixture in a
probe), and this module never re-implements a step of it.

TWO WRITE REGIMES, both configured per destination repo, never inferred:

  regime "git"    an ordinary clone this workflow owns. A rejected push is
                  integrated by MERGING the remote in and pushing again. Never a
                  rebase, never a force, and the remote side is never discarded.

  regime "vault"  a SHARED working tree the owner and other sessions also edit,
                  of which the destination is one subtree. The artifacts are
                  committed there by explicit pathspec — the only bound that
                  holds on a shared index — and a rejected push is completed
                  from a TEMPORARY WORKTREE OUTSIDE that tree, by cherry-picking
                  this cycle's own commits onto the remote branch. The shared
                  working tree is never merged into, never reset and never
                  swept, because other sessions hold uncommitted work in it.

Every destination name, path, branch, remote and timezone is CONFIGURATION read
through a config key. Nothing owner-specific is written into this file.

Run with --help for the command surface.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import destination_resolver
import file_lock

# Where per_meeting_job records the destination paths a summarize sitting changed.
PROPAGATED_FILE = "propagated.json"

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_SEAMS = TOOL_DIR.parent / "seams"

# The config KEY this layer reads. A key, never a path — the same binding
# `destination_resolver.config_path` defines, reused rather than restated.
TARGETS_KEY = "publish-targets"

# The two durable files this layer keeps under the state root.
JOURNAL = "publish-journal.jsonl"          # in-flight stages, for resume
PROCESSED = "processed-transcripts.jsonl"  # the `processed-transcript-store` seam

# per_meeting_job.py's settlement ledger — this layer only READS it, to carry a
# content-routed meeting's pick forward (see `settled_content_entity`). The
# filename duplicates per_meeting_job.py's own `OUTCOMES` constant rather than
# importing it: per_meeting_job.py already imports this module, so importing it
# back would cycle.
OUTCOMES_LOG = "outcomes.jsonl"

# The stage ladder. Order is the contract: `processed` is reachable only from
# `noted`, which is reachable only from `published`, and so on down.
STAGES = ("synced", "written", "committed", "published", "noted", "processed")

# The outcome vocabulary, quoted from the `failure-event-and-outcome` seam. No
# value outside this set is ever emitted.
OUTCOMES = ("filed", "amended", "withheld-unroutable", "skipped", "unprocessable",
            "failed")

REGIMES = ("git", "vault")

# How a filed transcript is told from the summary it sits beside. This module's
# OWN convention, defined once and read by both the writer and the discovery
# filter — never re-spelled at a second site.
TRANSCRIPT_INFIX = "-transcript-"

EXIT_OK = 0
EXIT_VERDICT = 1  # ran fine, the meeting did not publish
EXIT_REFUSED = 2  # could not run — same convention as the sibling tools


class Refused(Exception):
    """The layer could not run. Never an outcome, never a default."""


def refuse(what: str, why: str, fix: str) -> None:
    raise Refused(f"{what}: {why}\n  fix: {fix}")


# --------------------------------------------------------------- plumbing
def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    """One record, one line, one write.

    Concurrent cycles append to the same file, so the record is rendered first
    and handed to a single O_APPEND write: a partial line here would be read
    back as a corrupt store by the very pre-check that keeps work from being
    done twice.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, blob)
    finally:
        os.close(fd)


@contextmanager
def checkout_lock(checkout: Path):
    """Serialise the git critical section of one checkout.

    Two meetings of the same client on the same day are processed CONCURRENTLY
    (that is the probe, and the defect it exists for was a same-cycle race). Both
    land in the same working tree, and git's index is a single-writer structure:
    without this, one of the two cycles dies on `index.lock` rather than on
    anything the contract cares about. It guards the index only — the two files
    themselves never collide, because the discriminator makes their names
    different before any lock is taken.
    """
    checkout = Path(checkout)
    checkout.mkdir(parents=True, exist_ok=True)
    # Inside .git where there is one: a lock file in the working tree is an
    # untracked file left in the owner's repo (observed 2026-09-27).
    home = checkout / ".git" if (checkout / ".git").is_dir() else checkout
    handle = open(home / "publish-job.lock", "w", encoding="utf-8")
    try:
        file_lock.lock(handle.fileno())
        yield
    finally:
        file_lock.unlock(handle.fileno())
        handle.close()


# --------------------------------------------------------------- config
def load_targets(config_root: Path | None = None) -> dict:
    """The publish-target datum: one entry per destination repo, plus the
    discriminator's rendering. Read through the config key, never inlined."""
    datum = destination_resolver.config_datum(TARGETS_KEY, config_root)
    targets = datum.get("targets")
    if not isinstance(targets, dict) or not targets:
        refuse(f"config {TARGETS_KEY}", "'targets' is missing or empty",
               "declare one entry per destination repo")
    for name, target in targets.items():
        regime = target.get("regime")
        if regime not in REGIMES:
            refuse(f"config {TARGETS_KEY}",
                   f"target {name!r} declares regime {regime!r}",
                   f"regime must be one of {list(REGIMES)} — it is deployment fact, never inferred")
        for field in ("remote", "branch"):
            if not target.get(field):
                refuse(f"config {TARGETS_KEY}", f"target {name!r} has no {field!r}",
                       f"declare {field} — the target branch and remote are configuration")
    disc = datum.get("discriminator") or {}
    if not disc.get("format"):
        refuse(f"config {TARGETS_KEY}", "'discriminator.format' is missing",
               "declare the strftime format the meeting start renders through")
    return datum


def target_for(repo: str, targets: dict) -> dict:
    target = targets["targets"].get(repo)
    if not target:
        refuse(f"config {TARGETS_KEY}", f"no publish target declared for repo {repo!r}",
               f"add {repo!r} under 'targets', naming its regime, remote and branch")
    return {"repo": repo, **target}


# --------------------------------------------------------------- content routing
def settled_content_entity(state: Path, meeting_key: str) -> str | None:
    """The content-entity a prior settle() already stored for this meeting, if any.

    `destination_resolver.resolve()` re-derives a route from the job's own fields
    every time it runs; a meeting routed by CONTENT (a model's classification, not
    a deterministic participants/title match) carries no predicate a fresh job
    file can re-derive — the pick was made once, by per_meeting_job.py's settle()
    call, and rides in `outcomes.jsonl` from then on. The latest row wins (an
    amendment can resettle the same meeting).
    """
    entity = None
    for row in read_jsonl(Path(state) / OUTCOMES_LOG):
        if row.get("meeting-key") == meeting_key and row.get("content-entity"):
            entity = row["content-entity"]
    return entity


def resolve_job(job: dict, config_root, state: Path, routing: dict | None = None) -> dict:
    """`destination_resolver.resolve()`, carrying forward a settled content-entity.

    Every caller that resolves a job for publishing (precheck and the cycle
    alike) goes through here rather than calling `destination_resolver.resolve`
    directly, so a content-routed meeting never comes back `unroutable` on its
    second pass through the pipeline just because the job file itself never
    carried the pick.
    """
    if not job.get("content-entity"):
        entity = settled_content_entity(state, job["meeting-key"])
        if entity:
            job = {**job, "content-entity": entity}
    return destination_resolver.resolve(job, config_root, routing=routing)


# --------------------------------------------------------------- the discriminator
def discriminator(job: dict, targets: dict, routing: dict | None = None) -> str:
    """Rendered from the meeting's START, in the configured timezone. Nothing
    else feeds it: not the filing clock, not the transcript's arrival order."""
    signals = destination_resolver.meeting_signals(job)
    routing = routing if routing is not None else destination_resolver.load_routing()
    started = signals["start"].astimezone(routing["tzinfo"])
    return started.strftime(targets["discriminator"]["format"])


def discriminate(path: str, token: str, targets: dict) -> str:
    """Put the discriminator into one repo-relative path's stem.

    `insert-before`, when configured and present in the stem, keeps the owner's
    own filename suffix last (a summary stays recognisable as one); otherwise the
    token is appended to the stem. Either way the rule is ONE rule, and the
    transcripts get the result of it verbatim.

    Idempotent: a path already carrying the token in place is returned as is —
    the summarizer is told the discriminated name up front and writes it
    directly, so no undiscriminated draft is ever left in the destination.
    """
    p = Path(path)
    stem, suffix = p.stem, p.suffix
    anchor = targets["discriminator"].get("insert-before")
    if stem.endswith(f"-{token}") or (anchor and stem.endswith(f"-{token}{anchor}")):
        return p.as_posix()
    if anchor and stem.endswith(anchor):
        stem = f"{stem[: -len(anchor)]}-{token}{anchor}"
    else:
        stem = f"{stem}-{token}"
    return (p.parent / f"{stem}{suffix}").as_posix()


def transcript_paths(summary_path: str, sources) -> dict:
    """Clause 14: beside the summary, sharing the summary's stem — which is the
    DISCRIMINATED stem, so the discriminator lands on both or on neither."""
    p = Path(summary_path)
    return {source: (p.parent / f"{p.stem}{TRANSCRIPT_INFIX}{source}{p.suffix}").as_posix()
            for source in sources}


# --------------------------------------------------------------- git
def git(checkout: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(checkout), *args],
                          capture_output=True, text=True)
    if check and proc.returncode != 0:
        refuse("git", f"`git {' '.join(args)}` failed: {(proc.stderr or proc.stdout).strip()[:400]}",
               "inspect the checkout")
    return proc


def sync(target: dict, checkout: Path) -> dict:
    """Fetch, and fast-forward onto the remote branch where that is possible.

    This runs BEFORE the pre-check, which runs BEFORE any summary is produced:
    a summary someone else already filed is only visible once the remote has
    been fetched, and re-summarizing it is precisely the waste clause 13 forbids.
    Fast-forward only — this step never merges and never rewrites, in either
    regime.
    """
    fetched = git(checkout, "fetch", target["remote"], target["branch"])
    result = {"fetched": fetched.returncode == 0,
              "fetch-error": None if fetched.returncode == 0
              else (fetched.stderr or "").strip()[:400],
              "fast-forwarded": False, "diverged": False}
    if fetched.returncode != 0:
        return result
    merged = git(checkout, "merge", "--ff-only", "FETCH_HEAD")
    result["fast-forwarded"] = merged.returncode == 0
    result["diverged"] = merged.returncode != 0
    return result


def commit(target: dict, checkout: Path, paths: list[str], message: str) -> dict:
    """Stage and commit THIS cycle's paths, bound by explicit pathspec.

    `git commit -- <paths>` is the only bound that holds on a shared index: it
    re-resolves the paths at commit time, so a parallel session staging in the
    window between the check and the commit cannot ride along.
    """
    git(checkout, "add", "--", *paths, check=True)
    status = git(checkout, "status", "--porcelain", "--", *paths)
    if not status.stdout.strip():
        return {"committed": False, "why": "nothing to commit — the paths already match HEAD"}
    done = git(checkout, "commit", "-m", message, "--", *paths)
    if done.returncode != 0:
        refuse("git commit", (done.stderr or done.stdout).strip()[:400], "inspect the checkout")
    head = git(checkout, "rev-parse", "HEAD").stdout.strip()
    return {"committed": True, "head": head}


def dirty_paths(checkout: Path) -> set[str]:
    """Every changed or untracked path in the checkout, repo-relative."""
    listed = git(checkout, "status", "--porcelain", "-z", "--untracked-files=all").stdout
    return {entry[3:] for entry in listed.split("\0") if len(entry) > 3}


def head_unpublished(target: dict, checkout: Path) -> str | None:
    """Local HEAD, if it differs from the FETCHED remote tracking ref — else None.

    For a caller with no per-meeting journal (unlike `run_cycle`'s
    `unpublished_commits`): after a `sync()`, local HEAD equals the remote tip
    unless something committed locally without pushing — this cycle's own
    `commit()` call, or an earlier attempt that got that far and no further.
    Returns the ONE commit to push, never a range: `remote..HEAD` can carry a
    PEER's unpushed commits in a shared "vault" checkout (swept once, found
    2026-09-27) — a single named hash never can.
    """
    local = git(checkout, "rev-parse", "HEAD").stdout.strip()
    remote = git(checkout, "rev-parse", f"{target['remote']}/{target['branch']}")
    if remote.returncode != 0 or remote.stdout.strip() != local:
        return local or None
    return None


def propagated_paths(state: Path, meeting_key: str) -> list[str]:
    """The destination paths this meeting's summarize sitting changed, as
    per_meeting_job recorded them; [] when it recorded none."""
    record = Path(state) / "runs" / meeting_key / PROPAGATED_FILE
    if not record.is_file():
        return []
    return list(json.loads(record.read_text(encoding="utf-8")).get("paths", []))


def _push(target: dict, checkout: Path) -> subprocess.CompletedProcess:
    return git(checkout, "push", target["remote"], f"HEAD:{target['branch']}")


def _push_via_worktree(target: dict, checkout: Path, commits: list[str]) -> dict:
    """Publish from a shared tree WITHOUT touching it, and ONLY this cycle's commits.

    The shared working tree holds other sessions' uncommitted work, so it is
    never merged into, reset or swept. Its branch also holds other sessions'
    UNPUSHED commits, which are theirs to publish — so the commits sent are the
    ones this cycle recorded making, never `remote..HEAD` (that range swept a
    peer's unpushed commits along, found 2026-09-27). They are cherry-picked onto
    the fetched remote branch in a temporary worktree outside the tree.
    """
    base = f"{target['remote']}/{target['branch']}"
    if not commits:
        return {"pushed": False, "cause": "nothing of this cycle's own is unpushed"}
    scratch = Path(tempfile.mkdtemp(prefix="publish-job-worktree-"))
    tree = scratch / "wt"
    try:
        added = git(checkout, "worktree", "add", "--detach", str(tree), base)
        if added.returncode != 0:
            return {"pushed": False, "cause": f"worktree refused: {added.stderr.strip()[:200]}"}
        picked = git(tree, "cherry-pick", *commits)
        if picked.returncode != 0:
            git(tree, "cherry-pick", "--abort")
            return {"pushed": False,
                    "cause": f"the remote and this cycle conflict: {picked.stderr.strip()[:200]}"}
        pushed = git(tree, "push", target["remote"], f"HEAD:{target['branch']}")
        if pushed.returncode != 0:
            return {"pushed": False, "cause": (pushed.stderr or pushed.stdout).strip()[:300]}
        return {"pushed": True, "via": "worktree", "commits": commits}
    finally:
        git(checkout, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(scratch, ignore_errors=True)


def push(target: dict, checkout: Path, own: list[str], attempts: int = 3) -> dict:
    """Push inside this cycle, integrating a remote that moved under us.

    A rejected push means the owner (or another writer) committed to the remote
    between this cycle's fetch and its push. Their commit is INTEGRATED, never
    discarded: regime "git" merges the remote in and pushes again; regime
    "vault" cherry-picks onto the remote in a worktree outside the shared tree.
    No branch of this function force-pushes or rewrites published history.
    """
    trail = []
    if target["regime"] == "vault":
        # Never a direct push: HEAD carries other sessions' unpushed commits.
        for attempt in range(1, attempts + 1):
            fetched = git(checkout, "fetch", target["remote"], target["branch"])
            if fetched.returncode != 0:
                return {"pushed": False, "attempts": attempt, "trail": trail,
                        "cause": "the remote is unreachable: "
                                 + (fetched.stderr or "").strip()[:300]}
            done = _push_via_worktree(target, checkout, own)
            if done.get("pushed"):
                return {**done, "attempts": attempt, "trail": trail}
            trail.append({"attempt": attempt, "error": done.get("cause")})
        return {"pushed": False, "attempts": attempts, "trail": trail,
                "cause": trail[-1]["error"] if trail else "push failed"}
    for attempt in range(1, attempts + 1):
        attempted = _push(target, checkout)
        if attempted.returncode == 0:
            return {"pushed": True, "via": "direct", "attempts": attempt, "trail": trail}
        error = (attempted.stderr or attempted.stdout).strip()[:400]
        trail.append({"attempt": attempt, "error": error})
        fetched = git(checkout, "fetch", target["remote"], target["branch"])
        if fetched.returncode != 0:
            return {"pushed": False, "attempts": attempt, "trail": trail,
                    "cause": f"push failed and the remote is unreachable: {error}"}
        merged = git(checkout, "merge", "--no-edit", "FETCH_HEAD")
        if merged.returncode != 0:
            git(checkout, "merge", "--abort")
            return {"pushed": False, "attempts": attempt, "trail": trail,
                    "cause": "the remote side conflicts with this cycle and was NOT discarded: "
                             + (merged.stderr or merged.stdout).strip()[:300]}
    return {"pushed": False, "attempts": attempts, "trail": trail,
            "cause": "push still rejected after integrating the remote"}


# --------------------------------------------------------------- the stores
def unpublished_commits(state: Path, meeting_key: str) -> list[str]:
    """This meeting's commits since its last publication — what a vault push sends."""
    own: list[str] = []
    for row in journal_rows(state, meeting_key):
        if row["stage"] == "published":
            own = []
        elif row["stage"] == "committed" and row.get("head") and row["head"] not in own:
            own.append(row["head"])
    return own


def journal_rows(state: Path, meeting_key: str) -> list[dict]:
    return [row for row in read_jsonl(Path(state) / JOURNAL)
            if row.get("meeting-key") == meeting_key]


def reached(state: Path, meeting_key: str) -> str | None:
    """The furthest stage this meeting has completed, or None."""
    rows = journal_rows(state, meeting_key)
    if not rows:
        return None
    return max((row["stage"] for row in rows), key=lambda s: STAGES.index(s))


def note_stage(state: Path, meeting_key: str, stage: str, **fields) -> None:
    if stage not in STAGES:
        refuse("journal", f"unknown stage {stage!r}", f"use one of {list(STAGES)}")
    append_jsonl(Path(state) / JOURNAL,
                 {"meeting-key": meeting_key, "stage": stage, "at": now_stamp(), **fields})


def processed_records(state: Path) -> list[dict]:
    return read_jsonl(Path(state) / PROCESSED)


def processed_for(state: Path, meeting_key: str) -> list[dict]:
    return [row for row in processed_records(state) if row.get("meeting-key") == meeting_key]


def owner_of_path(state: Path, repo: str, path: str) -> str | None:
    """Which meeting a filed path belongs to, per the durable record.

    The binding is taken from the store and NOT from anything inside the file:
    the summarizer skills' own frontmatter keys are not stable across runs, so a
    layer that keyed amendment on a frontmatter field would rewrite the wrong
    meeting's summary the first time a key was renamed.
    """
    for row in processed_records(state):
        summary = row.get("summary") or {}
        if summary.get("repo") == repo and summary.get("path") == path:
            return row.get("meeting-key")
    return None


# --------------------------------------------------------------- the pre-check
def precheck(job: dict, routed: dict, target: dict, checkout: Path, state: Path,
             summary_path: str) -> dict:
    """Decide what this cycle must do, BEFORE a summary is produced.

    Three sources answer it, in order of authority: the durable processed record
    (which meeting owns which file), this layer's journal (a cycle that died
    part-way), and finally the destination itself on disk (a summary filed by
    hand, or by a writer that never reached the store).
    """
    key = job["meeting-key"]
    sources = sorted({record["source"] for record in job["source-set"]})
    records = processed_for(state, key)
    covered = sorted({source for row in records for source in row.get("coverage", [])})
    stage = reached(state, key)
    found = [item for item in destination_resolver.walk_summaries(checkout)
             if item.get("meeting-key") == key
             and TRANSCRIPT_INFIX not in Path(item["path"]).name]

    if records and set(sources) <= set(covered) and stage == "processed":
        return {"disposition": "already-done", "covered": covered,
                "summary": records[-1]["summary"],
                "why": "every source of this meeting is already in the filed summary"}
    if stage in ("written", "committed", "published", "noted"):
        # Only a cycle that got as far as putting text on disk is resumable. A
        # cycle that only synced has produced nothing to resume, and treating
        # its journal row as progress would skip the summarize step of every
        # first run.
        return {"disposition": "resume", "from-stage": stage, "covered": covered,
                "summary": {"repo": target["repo"], "path": summary_path},
                "why": f"a previous cycle stopped after '{stage}'"}
    if records:
        return {"disposition": "amend", "covered": covered,
                "summary": records[-1]["summary"],
                "why": "a summary for this meeting is filed and a source it does not cover arrived"}
    if found:
        return {"disposition": "amend", "covered": covered,
                "summary": {"repo": target["repo"],
                            "path": Path(found[0]["path"]).as_posix()},
                "why": "a summary carrying this meeting's key is already in the destination"}
    return {"disposition": "new", "covered": [], "why": "no summary exists for this meeting"}


def amend_target(state: Path, meeting_key: str, repo: str, path: str) -> None:
    """Refuse to rewrite a file that belongs to a different meeting.

    An amendment is keyed on the meeting key. A path whose recorded owner is
    another meeting is not amended and not overwritten — it is refused, because
    the alternative is destroying a summary nobody asked to touch.
    """
    owner = owner_of_path(state, repo, path)
    if owner is not None and owner != meeting_key:
        refuse("amend", f"{repo}:{path} is the filed summary of meeting {owner!r}, "
                        f"not of {meeting_key!r}",
               "amend the path this meeting's own record names")


# --------------------------------------------------------------- the cycle
def run_cycle(job: dict, *, config_root: Path, checkout_root: Path, state: Path,
              transcripts: dict, summarize, bus=None, config=None,
              routing=None) -> dict:
    """One meeting, from the destination sync to the fully-processed record.

    `summarize` is called ONLY after the destination has been synced and
    pre-checked, and ONLY when this cycle actually has to produce text. It is
    handed the routed destination and returns `{"text": ..., "path": ...}`;
    `path` is required exactly when the route delegates placement to the
    destination repo's own rules.
    """
    key = job["meeting-key"]
    state = Path(state)
    trace: list[str] = []
    targets = config if config is not None else load_targets(config_root)
    routing = routing if routing is not None else destination_resolver.load_routing(config_root)

    trace.append("resolve")
    routed = resolve_job(job, config_root, state, routing=routing)
    if routed["kind"] != "routed":
        # Clause 7: no route, no write. Not this layer's ask to make — it hands
        # the typed answer back untouched.
        return {"meeting-key": key, "outcome": "withheld-unroutable", "trace": trace,
                "unroutable": routed, "wrote": []}

    target = target_for(routed["destination"]["repo"], targets)
    checkout = Path(checkout_root) / target["repo"]
    token = discriminator(job, targets, routing)

    with checkout_lock(checkout):
        trace.append("sync")
        synced = sync(target, checkout)
        note_stage(state, key, "synced", **{"diverged": synced["diverged"]})

        placement = routed["destination"].get("placement")
        proposed = routed["destination"].get("path")

        trace.append("precheck")
        # The pre-check needs a path to look for; for a delegated placement the
        # destination repo's own rules choose it, so the lookup falls back to the
        # meeting key recorded in the stores and on disk.
        provisional = discriminate(proposed, token, targets) if proposed else ""
        decision = precheck(job, routed, target, checkout, state, provisional)

        if decision["disposition"] == "already-done":
            return {"meeting-key": key, "outcome": "filed", "trace": trace,
                    "precheck": decision, "wrote": [], "summarized": False,
                    "destination": decision["summary"],
                    "why": "the pre-check found this meeting fully processed; "
                           "nothing was summarized and nothing was written"}

        resuming = decision["disposition"] == "resume"
        summary_ref = decision.get("summary") or {}
        existing_path = summary_ref.get("path") or provisional

        if decision["disposition"] == "amend":
            amend_target(state, key, target["repo"], existing_path)

        landed = next((row for row in reversed(journal_rows(state, key))
                       if row["stage"] == "written"), None)

        if resuming and landed:
            # The text is already on disk from the killed cycle, and the journal
            # says so. Re-summarizing it would be the second write clause 13
            # forbids, and re-rendering the path could land a second file.
            trace.append("resume-skip-summarize")
            paths = list(landed["paths"])
            summary_path = paths[0]
            outcome = landed["outcome"]
            changed = landed["changed"]
        else:
            trace.append("summarize")
            produced = summarize({"job": job, "routed": routed, "decision": decision,
                                  "discriminator": token, "checkout": checkout})
            if decision["disposition"] == "amend":
                # In place. The path this meeting's own record names wins over a
                # freshly rendered one: a late twin amends the file that is
                # there, and never creates a second one.
                summary_path = existing_path
                amend_target(state, key, target["repo"], summary_path)
            elif placement == "template":
                summary_path = discriminate(proposed, token, targets)
            else:
                offered = produced.get("path")
                if not offered:
                    refuse("placement", "the route delegates placement to the destination repo "
                                        "and the summarizer returned no path",
                           "return the repo-relative path the destination's own rules chose")
                summary_path = discriminate(offered, token, targets)

            outcome = "amended" if decision["disposition"] == "amend" else "filed"

            trace.append("write-summary")
            target_file = checkout / summary_path
            before = target_file.read_text(encoding="utf-8") if target_file.exists() else None
            changed = before != produced["text"]
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(produced["text"], encoding="utf-8")
            paths = [summary_path]

            trace.append("write-transcripts")
            for source, path in transcript_paths(summary_path, sorted(transcripts)).items():
                handle = checkout / path
                handle.parent.mkdir(parents=True, exist_ok=True)
                handle.write_text(transcripts[source], encoding="utf-8")
                paths.append(path)
            note_stage(state, key, "written", paths=paths, changed=changed, outcome=outcome)

        destination = {"repo": target["repo"], "path": summary_path}

        trace.append("commit")
        # The propagation the destination's own rules asked the summarizer to
        # complete (CRM records, the meeting index, generated data) rides in the
        # same commit — exactly the paths the summarize sitting changed, never
        # a peer's (owner ruling, 2026-09-27: a correction's propagation is
        # committed alongside it, not left for a later cycle to notice).
        paths += [p for p in propagated_paths(state, key) if p not in paths]
        committed = commit(target, checkout,
                           paths,
                           f"summary and transcripts for meeting {key}")
        note_stage(state, key, "committed", **{"head": committed.get("head")})

        trace.append("push")
        own = unpublished_commits(state, key)
        if own:
            published = push(target, checkout, own)
            if not published.get("pushed"):
                cause = published.get("cause") or "push failed"
                # Clause 12/18: named, owner-visible, and the job is LEFT IN THE
                # JOURNAL at 'committed' so the next cycle resumes it. Nothing is
                # dropped and no processed record is written.
                if bus is not None:
                    bus({"kind": "failure-event", "scope": "meeting", "meeting-key": key,
                         "cause": f"publication to {target['repo']} failed: {cause}",
                         "at": now_stamp()})
                return {"meeting-key": key, "outcome": "failed", "trace": trace,
                        "precheck": decision, "wrote": paths, "destination": destination,
                        "cause": cause, "retryable": True, "published": published,
                        "why": "the artifacts are committed and the job stays in the journal "
                               "at 'committed'; the next cycle resumes at the push"}
        else:
            # `own` is empty: NO journal "committed" row for this meeting lacks
            # a later "published" row (`unpublished_commits`, above), from this
            # call or any earlier, interrupted one — and `unpublished_commits`
            # only counts a "committed" row with a REAL head, so a prior cycle
            # that also found nothing to commit (head: null) was never counted
            # either. So this meeting's destination bytes already match the
            # FETCHED REMOTE's HEAD: filed already, by the owner, a peer
            # session, or an earlier cycle of this same meeting. That is a
            # successful publish, not a push with nothing to send: calling
            # `push()` here would report "nothing of this cycle's own is
            # unpushed" (regime "vault"'s `_push_via_worktree` on an empty
            # commit list) and the caller used to treat that as a failure
            # forever — the meeting never reached `processed`, and a later
            # tick kept re-emitting it as new (measured live, 2026-09-28). A
            # REAL committed-but-unpushed head (a killed cycle that got as far
            # as `commit`, e.g.) makes `own` non-empty and still goes through
            # `push()` above, so it can still fail and still resumes correctly.
            trace.append("already-published")
            published = {"pushed": True, "via": "already-current"}
        note_stage(state, key, "published", via=published.get("via"))

        trace.append("filed-note")
        if bus is not None:
            if outcome == "amended":
                if changed:
                    bus({"kind": "amendment", "meeting-key": key,
                         "what-changed": "summary amended — a further source arrived",
                         "summary": destination})
            else:
                bus({"kind": "filed-note", "meeting-key": key, "destination": destination,
                     "meeting-title": destination_resolver.meeting_signals(job)["title"]})
        note_stage(state, key, "noted", **{"changed": changed})

        trace.append("processed-record")
        for record in job["source-set"]:
            append_jsonl(state / PROCESSED, {
                "transcript-ref": record["drive-ref"],
                "account": record["account"],
                "source": record["source"],
                "meeting-key": key,
                "processed-at": now_stamp(),
                "summary": destination,
                "coverage": sorted({r["source"] for r in job["source-set"]}),
            })
        note_stage(state, key, "processed")

    return {"meeting-key": key, "outcome": outcome, "trace": trace, "precheck": decision,
            "wrote": paths, "destination": destination, "discriminator": token,
            "changed": changed, "published": published, "synced": synced}


# --------------------------------------------------------------- the surface
def _read_json(path: str):
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_summarize(text_path: Path, offered: str | None):
    def summarize(_request):
        try:
            text = Path(text_path).read_text(encoding="utf-8")
        except OSError as exc:
            # A stale --summary path (the verdict that named it is no longer
            # current — the meeting's transcript is not gone, only the path a
            # prior pass reported is) is a REFUSAL, never a crash: measured
            # live, 2026-09-28 — an unhandled FileNotFoundError here was read
            # by the calling agent as "the file was deleted" and produced an
            # owner question on a false premise.
            refuse("summary", f"cannot read --summary {text_path}: {exc}",
                   "re-run per_meeting_job.py for this meeting to get a current "
                   "summary-file path, then retry cycle with it")
        answer = {"text": text}
        if offered:
            answer["path"] = offered
        return answer
    return summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish_job",
        description="File one meeting's summary and transcripts in the resolved destination "
                    "and publish them within the cycle.")
    sub = parser.add_subparsers(dest="command", required=True)

    cycle = sub.add_parser("cycle", help="run one meeting's filing and publication")
    cycle.add_argument("--job", required=True, help="a meeting-key-and-source-set JSON, or -")
    cycle.add_argument("--summary", required=True, type=Path,
                       help="the summary text this cycle files")
    cycle.add_argument("--summary-path",
                       help="repo-relative path, required only when the route delegates placement")
    cycle.add_argument("--transcript", action="append", default=[], metavar="SOURCE=FILE",
                       help="one transcript to file beside the summary (repeatable)")
    cycle.add_argument("--config-root", type=Path, help="the component config-module home")
    cycle.add_argument("--checkout-root", required=True, type=Path,
                       help="where destination repos are checked out (deployment config)")
    cycle.add_argument("--state", required=True, type=Path,
                       help="where the journal and the processed record live")

    check = sub.add_parser("precheck", help="what a cycle would do, without doing it")
    check.add_argument("--job", required=True)
    check.add_argument("--config-root", type=Path)
    check.add_argument("--checkout-root", required=True, type=Path)
    check.add_argument("--state", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "cycle":
            transcripts = {}
            for item in args.transcript:
                source, _, path = item.partition("=")
                transcripts[source] = Path(path).read_text(encoding="utf-8")
            result = run_cycle(
                _read_json(args.job),
                config_root=args.config_root,
                checkout_root=args.checkout_root,
                state=args.state,
                transcripts=transcripts,
                summarize=_file_summarize(args.summary, args.summary_path),
            )
        else:
            job = _read_json(args.job)
            targets = load_targets(args.config_root)
            routing = destination_resolver.load_routing(args.config_root)
            routed = resolve_job(job, args.config_root, args.state, routing=routing)
            if routed["kind"] != "routed":
                result = {"disposition": "unroutable", "routed": routed}
            else:
                target = target_for(routed["destination"]["repo"], targets)
                checkout = Path(args.checkout_root) / target["repo"]
                token = discriminator(job, targets, routing)
                proposed = routed["destination"].get("path")
                result = precheck(job, routed, target, checkout, Path(args.state),
                                  discriminate(proposed, token, targets) if proposed else "")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Refused as exc:
        print(f"publish_job: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_OK if result.get("outcome") in ("filed", "amended") or args.command == "precheck" \
        else EXIT_VERDICT


if __name__ == "__main__":
    raise SystemExit(main())
