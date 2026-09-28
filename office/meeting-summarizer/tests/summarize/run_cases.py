#!/usr/bin/env python3
"""m6 case driver — the six fixture cases of design.md § m6, each with its threshold.

Every case is run for real against its own materialised fixture copy outside the
product tree, under the write counter in harness.py. Each case is ALSO run in a
RED arm: a single change to the case that must flip its verdict, so a green here
is a measurement and not the absence of one.

  ./run_cases.py              every case, red arms included
  ./run_cases.py --only c d   just those cases
  ./run_cases.py --no-skill   only the cases that never invoke a summarizer

Exit 0 when every arm holds, 1 otherwise. The printed table is the evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from harness import FIXTURES, WriteCount, default_runs_root, manifest, materialise

import channel_protocol
import per_meeting_job

DOUBT = re.compile(r"\{\{doubt\|term=([^|}]+)\|guess=([^}]*)\}\}")
# Any OTHER notation a summary might reach for to flag an unsettled term. The
# marker probe's second count is over these: clause 28's cross-meeting matching
# keys on the one shape, and a second notation breaks it silently.
OTHER_NOTATIONS = (
    # The sharpest one: a double-brace construct that is NOT the seam's marker —
    # a second notation in the marker's own family is exactly what clause 28's
    # matching would slide past.
    ("double-brace-not-the-marker", re.compile(r"\{\{(?!doubt\|term=)[^}\n]{0,80}\}\}")),
    ("single-brace-doubt", re.compile(r"(?<!\{)\{\s*(doubt|d[uú]vida)[^}\n]*\}")),
    ("bracket-sic", re.compile(r"\[\s*sic\s*\??\s*\]", re.I)),
    ("bracket-uncertain", re.compile(r"\[\s*(inaud[ií]vel|inaudible|indistinto|incerto|uncertain)[^\]\n]*\]", re.I)),
    ("paren-question", re.compile(r"\(\s*\?+\s*\)")),
    ("paren-sic", re.compile(r"\(\s*sic\s*\)", re.I)),
    ("angle-uncertain", re.compile(r"<\s*(uncertain|incerto|d[uú]vida|\?)[^>\n]*>")),
    ("grafia-incerta", re.compile(r"\(\s*(grafia|ortografia|nome|escrita)\s+incert[ao][^)\n]*\)", re.I)),
    ("doubt-label-line", re.compile(r"^\s*[-*]?\s*(doubt|d[uú]vida)\s*:", re.I | re.M)),
)
# Deliberately NOT here: a bare TODO/FIXME/"confirmar" scan. `todo` is an ordinary
# Portuguese word ("cobre todo o escopo") and a case-insensitive acronym scan over a
# Portuguese summary reports prose as notation — measured on the first run of this
# probe. A checker that fires on the language the document is written in tells you
# nothing about the notation.

# Case (a): the five utterances where Meet and Tactiq differ. The Meet reading is
# what a correct summary carries; the Tactiq reading must appear ZERO times.
CASE_A_DIFFERENCES = (
    ("orcamento", "quarenta e oito", "oitenta e quatro"),
    ("data de corte", "dezenove", "vinte e nove"),
    ("plataforma", "EXAMPLE-Ledgerly", "Legerly"),
    ("escopo fase 2", "reduzir", "ampliar"),
    ("build", "Kappa-7", "Kappa-sete"),
)
# Tactiq-side tokens that must not survive into the summary. Only tokens that do
# not also occur inside the Meet reading are listed — "Legerly" is a substring of
# nothing in "EXAMPLE-Ledgerly", which is why that pair is checkable at all.
CASE_A_TACTIQ_TOKENS = ("oitenta e quatro", "vinte e nove", "Kappa-sete", "ampliar")


class Arm:
    """One asserted threshold, with the number that settled it."""

    def __init__(self, case: str, name: str):
        self.case, self.name, self.checks = case, name, []

    def hold(self, label: str, ok: bool, detail) -> None:
        self.checks.append({"label": label, "ok": bool(ok), "detail": detail})

    @property
    def ok(self) -> bool:
        return all(check["ok"] for check in self.checks)


def run_job(case: str, job_name: str, runs_root: Path, *, auxiliary=True,
            binding_edit=None, replies=None, cycles: int = 1) -> dict:
    """Materialise, then run the job `cycles` times, counting every write."""
    scaffold = materialise(case, runs_root)
    binding = json.loads((scaffold["root"] / "artifacts" / "binding.json").read_text("utf-8"))
    if not auxiliary:
        binding["auxiliary"] = {}
    if binding_edit:
        binding_edit(binding)
    (scaffold["root"] / "artifacts" / "binding.json").write_text(
        json.dumps(binding, ensure_ascii=False, indent=2), encoding="utf-8")

    job = json.loads((FIXTURES / "jobs" / f"{job_name}.json").read_text("utf-8"))
    before = manifest(scaffold["checkout"])
    outcomes, counters = [], []
    for cycle in range(cycles):
        if replies and cycle in replies:
            scaffold["channel"].mkdir(parents=True, exist_ok=True)
            with (scaffold["channel"] / "replies.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(replies[cycle], ensure_ascii=False) + "\n")
        counter = WriteCount({"destination": scaffold["checkout"],
                              "channel": scaffold["channel"],
                              "state": scaffold["state"],
                              "work": scaffold["work"]})
        with counter:
            outcomes.append(per_meeting_job.run(
                job,
                artifacts=json.loads(
                    (scaffold["root"] / "artifacts" / "binding.json").read_text("utf-8")),
                config_root=scaffold["config"],
                checkout_root=scaffold["checkout"],
                channel_root=scaffold["channel"],
                state=scaffold["state"],
                work=scaffold["work"],
                seams=(FIXTURES.parent.parent.parent / "seams"),
                store=scaffold["channel"] / "stores" / "thread-meeting-map.jsonl"))
        counters.append(counter.report())
    after = manifest(scaffold["checkout"])
    added = sorted(set(after) - set(before))
    changed = sorted(name for name in set(after) & set(before) if after[name] != before[name])
    result = {"case": case, "scaffold": {k: str(v) for k, v in scaffold.items() if k != "binding"},
              "outcomes": outcomes, "counters": counters, "added": added, "changed": changed,
              "messages": channel_messages(scaffold["channel"]),
              "outcome-rows": rows(scaffold["state"] / "outcomes.jsonl"),
              "completion-rows": rows(scaffold["state"] / "completions.jsonl")}
    (scaffold["root"] / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return result


def rows(path: Path) -> list:
    if not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text("utf-8").splitlines() if line.strip()]


def channel_messages(channel: Path) -> list:
    return rows(Path(channel) / "messages.jsonl")


def summary_text(result: dict) -> str:
    target = result["outcomes"][-1].get("summary-file")
    if target and Path(target).is_file():
        return Path(target).read_text(encoding="utf-8")
    for name in result["added"]:
        path = Path(result["scaffold"]["checkout"]) / name
        if path.suffix == ".md":
            return path.read_text(encoding="utf-8")
    return ""


# ------------------------------------------------------------------- the cases
def case_a(runs_root: Path) -> list[Arm]:
    green = run_job("case-a", "case-a", runs_root)
    red = run_job("case-a-red-no-notes", "case-a", runs_root, auxiliary=False)
    text, red_text = summary_text(green), summary_text(red)
    merge = green["outcomes"][-1]["merge"]

    arm = Arm("a", "one summary; Meet wins every differing utterance; Gemini still disambiguates")
    arm.hold("exactly one artifact added to the destination", len(green["added"]) == 1, green["added"])
    arm.hold("no destination file was rewritten", not green["changed"], green["changed"])
    arm.hold("outcome is filed", green["outcomes"][-1].get("outcome") == "filed",
             green["outcomes"][-1].get("outcome"))
    arm.hold("every differing utterance took the Meet wording",
             merge["differing"] == 5 and merge["meet-wins"] == merge["differing"],
             {"differing": merge["differing"], "meet-wins": merge["meet-wins"],
              "compared": merge["compared"]})
    arm.hold("Tactiq coverage the Meet file lacks is carried, not dropped",
             merge["tactiq-only"] == 1, merge["tactiq-only"])
    hits = {token: text.count(token) for token in CASE_A_TACTIQ_TOKENS}
    arm.hold("zero Tactiq-only wordings survive into the summary",
             sum(hits.values()) == 0, hits)
    # Clause 19 says the notes WIN the disambiguation; it does not say they SETTLE
    # the term. A notes file is auxiliary, not owner-confirmed, so the skill may
    # still flag the name for the owner — and when it does, the reading that
    # stands in the marker must be the notes' reading and not a fallback. That is
    # what "applied" means here, and it is what the RED arm flips.
    xandi = [(term, guess) for term, guess in DOUBT.findall(text)
             if "xandi" in term.casefold()]
    arm.hold("the notes' reading of the name neither transcript spells is what stands",
             "EXAMPLE-Xandari" in text, {"EXAMPLE-Xandari": text.count("EXAMPLE-Xandari")})
    arm.hold("where the name is still flagged, the GUESS is the notes' reading",
             all(guess.strip() == "EXAMPLE-Xandari" for _, guess in xandi),
             xandi or "not flagged at all in this run")
    # Curation, tested on a fact the notes carry and the transcripts do NOT: the
    # Tactiq-only utterance says the divergence report "sai na segunda" and names
    # nobody; only the notes say EXAMPLE-Brum owns it. An attribution that reaches
    # the summary can only have come from the notes.
    curated = re.search(r"(EXAMPLE-Brum[^\n]{0,160}relat|relat[^\n]{0,160}EXAMPLE-Brum)",
                        text, re.I)
    arm.hold("the Gemini curation reached the summary (an attribution only the notes carry)",
             bool(curated), curated.group(0)[:120] if curated else None)
    arm.hold("the second, transcript-contradicted note item is surfaced rather than asserted",
             bool(re.search(r"fase\s+(tr[eê]s|3)", text, re.I)),
             bool(re.search(r"fase\s+(tr[eê]s|3)", text, re.I)))
    arm.hold("a term neither the glossary nor the notes settle still carries the marker",
             any("plunfar" in term.casefold() for term, _ in DOUBT.findall(text)),
             DOUBT.findall(text))
    red_xandi = [(term, guess) for term, guess in DOUBT.findall(red_text)
                 if "xandi" in term.casefold()]
    arm.hold("RED — with the notes removed, the name is absent AND the guess falls back",
             "EXAMPLE-Xandari" not in red_text
             and all(guess.strip() != "EXAMPLE-Xandari" for _, guess in red_xandi),
             {"EXAMPLE-Xandari in red summary": red_text.count("EXAMPLE-Xandari"),
              "red markers for the name": red_xandi})
    return [arm]


def case_b(runs_root: Path) -> list[Arm]:
    green = run_job("case-b", "case-b", runs_root)
    merge = green["outcomes"][-1]["merge"]

    def rebind(binding):
        """The same single-source job, over a transcript with nothing in it."""
        binding["artifacts"]["drv:file/FIXTURE-b-tactiq"]["location"] = \
            binding["artifacts"]["drv:file/FIXTURE-f-meet"]["location"]
    red = run_job("case-b-red-empty-source", "case-b", runs_root, binding_edit=rebind)

    arm = Arm("b", "one summary from Tactiq alone")
    arm.hold("exactly one artifact added to the destination", len(green["added"]) == 1, green["added"])
    arm.hold("outcome is filed", green["outcomes"][-1].get("outcome") == "filed",
             green["outcomes"][-1].get("outcome"))
    arm.hold("one source, so nothing was cross-referenced",
             merge["sources"] == ["tactiq"] and merge["compared"] == 0, merge)
    arm.hold("the summary is not empty", len(summary_text(green)) > 200, len(summary_text(green)))
    arm.hold("RED — the same single-source job over an empty transcript files nothing",
             red["outcomes"][-1]["action"] == "zero-utterance" and not red["added"],
             {"action": red["outcomes"][-1]["action"], "added": red["added"]})
    return [arm]


def case_c(runs_root: Path) -> list[Arm]:
    green = run_job("case-c", "case-c", runs_root)
    counts = green["counters"][-1]["counts"]

    def rebind(binding):
        binding["artifacts"]["drv:file/FIXTURE-c-gemini"]["location"] = \
            binding["artifacts"]["drv:file/FIXTURE-d-meet"]["location"]
        binding["artifacts"]["drv:file/FIXTURE-c-gemini"]["name"] = "EXAMPLE-Delta - Transcricao"
    red = run_job("case-c-red-real-transcript", "case-c", runs_root, binding_edit=rebind)

    # Clause 19 as amended 2026-09-27 (owner ruling r-gemini-notes-alone-triggers-summary):
    # notes alone ARE summarized — from the notes, with the notes-only label.
    arm = Arm("c", "a notes artifact alone is summarized from the notes, labelled notes-only")
    arm.hold("the job summarized the meeting", green["outcomes"][-1]["action"] == "summarized",
             green["outcomes"][-1]["action"])
    prompts = sorted(runs_root.glob("case-c/**/prompt.txt"))
    prompt = prompts[-1].read_text(encoding="utf-8") if prompts else ""
    arm.hold("the summarizer was told the notes are the ONLY source and to label it",
             "the ONLY source" in prompt and per_meeting_job.NOTES_ONLY_LABEL in prompt,
             [p.as_posix() for p in prompts])
    arm.hold("a summary landed in the destination", bool(green["added"]), green["added"])
    arm.hold("RED — the same job over a real transcript is NOT labelled notes-only",
             red["outcomes"][-1]["action"] == "summarized"
             and not red["outcomes"][-1].get("notes-only"), red["outcomes"][-1]["action"])
    return [arm]


def case_d(runs_root: Path) -> list[Arm]:
    green = run_job("case-d", "case-d", runs_root)
    counts = green["counters"][-1]["counts"]
    asks = [m for m in green["messages"] if m["type"] == "routing-ask"]

    red = run_job("case-d-red-routable", "case-b", runs_root)  # a routable meeting writes

    arm = Arm("d", "an ask is emitted and the write count before the answer is 0")
    arm.hold("an ask was emitted", green["outcomes"][-1]["action"] == "asked" and len(asks) == 1,
             {"action": green["outcomes"][-1]["action"], "routing-asks": len(asks)})
    # THE COUNT, and what one number can and cannot prove. The in-process counter
    # sees every write the job makes itself, bucketed; it CANNOT see a write made
    # by the summarizer subprocess — measured in the RED arm below, where a run
    # that files a real summary still reads `destination: 0`. So the zero is
    # asserted as three measures together: every bucket the job writes through is
    # 0 except the channel (which carries the ask, and an ask nobody can read is
    # not an ask); the summarizer was never launched; and the destination tree is
    # byte-identical. Each of the three is shown to discriminate by the RED arm.
    arm.hold("every counted bucket is 0 except the channel, which carries the ask",
             all(counts[b] == 0 for b in ("destination", "state", "work", "elsewhere"))
             and counts["channel"] > 0, counts)
    arm.hold("ZERO subprocesses — the summarizer was never reached",
             green["counters"][-1]["subprocesses"] == 0, green["counters"][-1]["subprocesses"])
    arm.hold("the destination tree is byte-identical before and after",
             not green["added"] and not green["changed"],
             {"added": green["added"], "changed": green["changed"]})
    arm.hold("nothing was settled — the meeting is still waiting on the owner",
             not green["outcome-rows"], green["outcome-rows"])
    arm.hold("RED — a routable meeting under the same probe launches the summarizer, "
             "writes through the job's own buckets, and lands a file",
             red["counters"][-1]["subprocesses"] == 1
             and red["counters"][-1]["counts"]["state"] > 0
             and len(red["added"]) == 1,
             {"subprocesses": red["counters"][-1]["subprocesses"],
              "counts": red["counters"][-1]["counts"], "added": red["added"],
              "note": "in-process destination count is 0 here TOO — the summarizer "
                      "subprocess writes the file, which is why that number alone "
                      "proves nothing and is never the whole assertion"})
    return [arm]


def case_e(runs_root: Path) -> list[Arm]:
    # The thread id is DERIVED from the meeting key by the channel engine itself
    # (`thr-` + a digest); typing one would land the reply on a thread nobody
    # mapped and the answer would never be found.
    thread = channel_protocol.thread_id_for("mtg-m6-e")
    skip_reply = {"id": "reply-skip", "thread": thread,
                  "text": "skip", "at": "2026-04-02T20:00:00-03:00"}
    green = run_job("case-e", "case-e", runs_root, replies={1: skip_reply}, cycles=3)
    first, second, third = green["outcomes"]
    after_ask = len([m for m in green["messages"] if m["type"] == "routing-ask"])
    per_cycle = [c["counts"]["destination"] for c in green["counters"]]

    named = {"id": "reply-dest", "thread": thread,
             "text": "arquivar em alpha-works", "at": "2026-04-02T20:00:00-03:00"}
    red = run_job("case-e-red-named-destination", "case-e", runs_root,
                  replies={1: named}, cycles=2)

    arm = Arm("e", "an ask; on `skip` zero writes, a processed record, and no re-ask")
    arm.hold("cycle 1 emitted the ask", first["action"] == "asked", first["action"])
    arm.hold("cycle 2 applied the answer as a skip", second["action"] == "skipped", second["action"])
    arm.hold("destination write count is 0 in EVERY cycle",
             per_cycle == [0, 0, 0], per_cycle)
    arm.hold("a processed-as-skipped record was written",
             len(green["outcome-rows"]) == 1
             and green["outcome-rows"][0]["outcome"] == "skipped"
             and len(green["completion-rows"]) == 1
             and green["completion-rows"][0]["answered-kind"] == "routing",
             {"outcomes": green["outcome-rows"], "completions": green["completion-rows"]})
    arm.hold("cycle 3 emitted NO re-ask", after_ask == 1 and third["action"] == "already-settled",
             {"routing-asks in the whole channel": after_ask, "cycle 3": third["action"]})
    arm.hold("RED — an answer naming a destination is NOT read as a skip",
             red["outcomes"][-1]["action"] == "answered-unknown-destination"
             and not red["outcome-rows"],
             {"action": red["outcomes"][-1]["action"], "rows": red["outcome-rows"]})
    return [arm]


def case_f(runs_root: Path) -> list[Arm]:
    green = run_job("case-f", "case-f", runs_root, cycles=2)
    notes = [m for m in green["messages"] if m["type"] == "failure-note"]

    def rebind(binding):
        binding["artifacts"]["drv:file/FIXTURE-f-meet"]["location"] = \
            binding["artifacts"]["drv:file/FIXTURE-d-meet"]["location"]
    red = run_job("case-f-red-has-utterances", "case-f", runs_root, binding_edit=rebind)

    arm = Arm("f", "no summary, exactly one note, recorded processed")
    arm.hold("the job stopped at the zero-utterance verdict",
             green["outcomes"][0]["action"] == "zero-utterance", green["outcomes"][0]["action"])
    arm.hold("no summary artifact",
             not green["added"] and not green["changed"] and green["counters"][0]["counts"]["destination"] == 0,
             {"added": green["added"], "destination-writes": green["counters"][0]["counts"]["destination"]})
    arm.hold("exactly ONE note", len(notes) == 1 and len(green["messages"]) == 1,
             {"failure-notes": len(notes), "messages": len(green["messages"])})
    arm.hold("recorded processed", len(green["outcome-rows"]) == 1
             and green["outcome-rows"][0]["outcome"] == "unprocessable",
             green["outcome-rows"])
    arm.hold("a second cycle re-notes nothing",
             green["outcomes"][1]["action"] == "already-settled" and len(green["messages"]) == 1,
             {"cycle 2": green["outcomes"][1]["action"], "messages": len(green["messages"])})
    arm.hold("RED — the same job over a transcript with utterances is not zero-utterance",
             red["outcomes"][-1]["action"] != "zero-utterance", red["outcomes"][-1]["action"])
    return [arm]


def marker_probe(runs_root: Path, produced: list[Path]) -> Arm:
    """The two counts: every unresolved term matches the seam shape, zero use another."""
    arm = Arm("marker", "the doubt marker is the only doubt notation")
    shape = json.loads(
        (FIXTURES.parent.parent.parent / "seams" / "doubt-flag-marker.schema.json")
        .read_text("utf-8"))["properties"]["marker-syntax"]["const"]
    arm.hold("the shape asserted is the seam's own const, read at run time",
             shape == "{{doubt|term=<term>|guess=<best-guess>}}", shape)
    matched, others = 0, {}
    for path in produced:
        text = path.read_text(encoding="utf-8")
        matched += len(DOUBT.findall(text))
        for name, pattern in OTHER_NOTATIONS:
            found = pattern.findall(text)
            if found:
                others.setdefault(name, []).append({"file": path.name, "hits": found[:5]})
    # The first count. It is an AGGREGATE over every summary this run produced:
    # a summary whose terms the glossary and the notes all settled correctly
    # carries no marker, and that is right, not a miss. The fixture set contains
    # terms nothing can settle, so a zero here means the marker never reached a
    # summary at all.
    arm.hold("every unresolved term matches the marker shape", matched > 0,
             {"markers matched": matched, "summaries scanned": len(produced)})
    arm.hold("ZERO use any other notation", not others, others or 0)
    poisoned = runs_root / "marker-red.md"
    poisoned.write_text(
        (produced[0].read_text("utf-8") if produced else "") + "\n- o nome [sic?] ficou incerto\n",
        encoding="utf-8")
    red = any(pattern.search(poisoned.read_text("utf-8")) for _, pattern in OTHER_NOTATIONS)
    arm.hold("RED — a second notation injected into a copy IS detected", red, red)
    return arm


CASES = {"a": case_a, "b": case_b, "c": case_c, "d": case_d, "e": case_e, "f": case_f}
SKILL_CASES = {"a", "b", "d"}  # d's RED arm files a real summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", choices=sorted(CASES), help="run just these cases")
    parser.add_argument("--no-skill", action="store_true",
                        help="skip the cases that invoke a summarizer")
    parser.add_argument("--runs-root", type=Path, default=default_runs_root())
    args = parser.parse_args(argv)

    chosen = args.only or sorted(CASES)
    if args.no_skill:
        chosen = [case for case in chosen if case not in SKILL_CASES]
    args.runs_root.mkdir(parents=True, exist_ok=True)

    arms: list[Arm] = []
    for case in chosen:
        arms += CASES[case](args.runs_root)

    produced = sorted(p for p in args.runs_root.rglob("checkout/**/*-resumo.md"))
    if produced:
        arms.append(marker_probe(args.runs_root, produced))

    width = max((len(check["label"]) for arm in arms for check in arm.checks), default=10)
    failures = 0
    for arm in arms:
        print(f"\n=== case ({arm.case}) — {arm.name}")
        for check in arm.checks:
            mark = "PASS" if check["ok"] else "FAIL"
            failures += 0 if check["ok"] else 1
            print(f"  [{mark}] {check['label']:<{width}}  {json.dumps(check['detail'], ensure_ascii=False, default=str)}")
    print(f"\nsummaries produced: {len(produced)}")
    for path in produced:
        print(f"  {path}")
    print(f"\narms: {len(arms)}  checks: {sum(len(a.checks) for a in arms)}  failures: {failures}")
    (args.runs_root / "arms.json").write_text(
        json.dumps([{"case": a.case, "name": a.name, "checks": a.checks} for a in arms],
                   ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
