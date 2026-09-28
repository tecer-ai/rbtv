"""The red arms — one deliberate defect per probe case.

A green probe is worth nothing until it has been seen RED. Each mutation below
breaks exactly one of the behaviours a case asserts, and the case it is paired
with must FAIL while it is applied. They are applied by MONKEYPATCHING the loaded
module, never by editing a file: an in-place source mutation leaves a stale
bytecode cache that can serve the previous mutant's verdict.

Applied from `$M7_MUTATION`, so the probe's own subprocesses (the concurrency
arms and the kill victim) carry the same mutation as the process that launched
them.
"""

from __future__ import annotations

import os

import publish_job as P


def _precheck_always_new(_module):
    """(a) the pre-check never recognises work already done."""
    def precheck(job, routed, target, checkout, state, summary_path):
        return {"disposition": "new", "covered": [], "why": "MUTANT: always new"}
    P.precheck = precheck


def _no_discriminator(_module):
    """(b) the meeting's start time stops reaching the filename."""
    P.discriminate = lambda path, token, targets: path


def _amend_renders_a_fresh_path(_module):
    """(c) a late twin renders a new path instead of amending the filed one."""
    real = P.precheck

    def precheck(job, routed, target, checkout, state, summary_path):
        decision = real(job, routed, target, checkout, state, summary_path)
        if decision["disposition"] == "amend":
            decision["summary"] = {"repo": target["repo"], "path": summary_path + ".v2.md"}
        return decision
    P.precheck = precheck


def _amend_ignores_the_key(_module):
    """(c) the amendment stops checking whose file it is about to rewrite."""
    P.amend_target = lambda state, meeting_key, repo, path: None


def _push_failure_is_silent(_module):
    """(d) a failed publication reports nothing and leaves nothing to retry."""
    real = P.push

    def push(target, checkout, attempts=3):
        result = real(target, checkout, attempts)
        if not result.get("pushed"):
            # the shape a DROPPED job takes: the failure is swallowed and the
            # cycle walks on as though it had published
            return {"pushed": True, "via": "pretend"}
        return result
    P.push = push


def _resolve_by_discarding_the_remote(_module):
    """(e) the rejection is SEEN and then won by force — the owner's commit is dropped.

    Deliberately keeps the rejection in the trail, so the case cannot go red
    merely on "the race never happened": what fails here is the owner's own line
    still being on the remote, which is the claim the criterion actually makes.
    """
    def push(target, checkout, attempts=3):
        first = P._push(target, checkout)
        if first.returncode == 0:
            return {"pushed": True, "via": "direct", "attempts": 1, "trail": []}
        trail = [{"attempt": 1, "error": (first.stderr or "").strip()[:400]}]
        forced = P.git(checkout, "push", "--force", target["remote"], f"HEAD:{target['branch']}")
        return {"pushed": forced.returncode == 0, "via": "direct", "attempts": 2, "trail": trail}
    P.push = push


def _processed_record_before_the_push(_module):
    """(f) 'fully processed' is written while the push is still outstanding."""
    real = P.commit

    def commit(target, checkout, paths, message):
        done = real(target, checkout, paths, message)
        P.append_jsonl(commit.state / P.PROCESSED,
                       {"meeting-key": commit.key, "summary": {"repo": target["repo"],
                                                               "path": paths[0]},
                        "coverage": ["meet"], "transcript-ref": "MUTANT", "account": "MUTANT",
                        "source": "meet", "processed-at": P.now_stamp()})
        P.note_stage(commit.state, commit.key, "processed")
        return done
    # the two values the real commit does not receive, taken from the cycle itself
    real_cycle = P.run_cycle

    def run_cycle(job, **kwargs):
        commit.state = kwargs["state"]
        commit.key = job["meeting-key"]
        return real_cycle(job, **kwargs)
    P.commit = commit
    P.run_cycle = run_cycle


def _transcripts_get_their_own_stem(_module):
    """(9) the transcripts stop sharing the summary's discriminated stem."""
    from pathlib import Path

    def transcript_paths(summary_path, sources):
        p = Path(summary_path)
        return {source: (p.parent / f"transcript-{source}{p.suffix}").as_posix()
                for source in sources}
    P.transcript_paths = transcript_paths


MUTATIONS = {
    "precheck-always-new": _precheck_always_new,
    "no-discriminator": _no_discriminator,
    "amend-renders-a-fresh-path": _amend_renders_a_fresh_path,
    "amend-ignores-the-key": _amend_ignores_the_key,
    "push-failure-is-silent": _push_failure_is_silent,
    "resolve-by-discarding-the-remote": _resolve_by_discarding_the_remote,
    "processed-record-before-the-push": _processed_record_before_the_push,
    "transcripts-get-their-own-stem": _transcripts_get_their_own_stem,
}


def apply_from_env() -> str | None:
    name = os.environ.get("M7_MUTATION")
    if not name:
        return None
    if name not in MUTATIONS:
        raise SystemExit(f"unknown mutation {name!r}; known: {sorted(MUTATIONS)}")
    MUTATIONS[name](P)
    return name
