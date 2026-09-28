#!/usr/bin/env python3
"""transcript-merge — cross-reference one meeting's transcripts into ONE text.

goal.md clause 5: where Meet and Tactiq both cover a meeting and both are
legible, MEET's wording wins on every utterance where they differ. Clause 19:
an auxiliary notes artifact (a Gemini notes file) is carried beside the merged
text for disambiguation and curation — it never overrides raw wording, and it
never appears here on its own.

The merge is DETERMINISTIC and its verdict is COUNTED: every pair the two
sources both cover is decided by rule, and the decision log says how many
differed and how many of those took Meet's wording. Deciding this in the
summarizing agent instead would make clause 5 a matter of opinion.

Deterministic: string scans only. No network, no model call.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from artifact_reader import utterances

EXIT_OK = 0
EXIT_REFUSED = 2

# Two sources of the same meeting start their clocks a minute or two apart, so
# utterances are aligned on seconds-from-the-source's-own-first-utterance.
ALIGN_TOLERANCE_SECONDS = 30

CLOCK = re.compile(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})")
# Meet's wording wins; Tactiq's is kept beside it only where the two differ by
# more than spacing and case, which is not a difference in wording.
NORMALISE = re.compile(r"[\s ]+")


def refuse(what: str, fix: str) -> None:
    print(f"transcript-merge refused: {what}\n  fix: {fix}", file=sys.stderr)
    raise SystemExit(EXIT_REFUSED)


def seconds(stamp: str) -> int | None:
    match = CLOCK.search(stamp or "")
    if not match:
        return None
    hours, minutes, secs = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(secs)


def offsets(items: list[dict]) -> list[dict]:
    """Utterances re-clocked to seconds from this source's own first utterance."""
    stamps = [seconds(item["at"]) for item in items]
    base = next((value for value in stamps if value is not None), 0)
    out = []
    for item, value in zip(items, stamps):
        out.append({**item, "offset": (value - base) if value is not None else None})
    return out


def same_wording(left: str, right: str) -> bool:
    return NORMALISE.sub(" ", left).strip().casefold() == NORMALISE.sub(" ", right).strip().casefold()


def align(meet: list[dict], tactiq: list[dict]) -> list[dict]:
    """Greedy one-to-one alignment in time order.

    A Tactiq utterance pairs with the nearest unclaimed Meet utterance within the
    tolerance. Unpaired utterances from EITHER source are carried through: a
    source that heard something the other missed is coverage, and dropping it
    would be a silent skip (clause 1).
    """
    claimed: set[int] = set()
    pairs: list[dict] = []
    for right in tactiq:
        best, best_gap = None, None
        for index, left in enumerate(meet):
            if index in claimed or left["offset"] is None or right["offset"] is None:
                continue
            gap = abs(left["offset"] - right["offset"])
            if gap <= ALIGN_TOLERANCE_SECONDS and (best_gap is None or gap < best_gap):
                best, best_gap = index, gap
        if best is None:
            pairs.append({"meet": None, "tactiq": right})
        else:
            claimed.add(best)
            pairs.append({"meet": meet[best], "tactiq": right})
    for index, left in enumerate(meet):
        if index not in claimed:
            pairs.append({"meet": left, "tactiq": None})
    return sorted(pairs, key=lambda pair: _order(pair))


def _order(pair: dict) -> tuple:
    left, right = pair["meet"], pair["tactiq"]
    chosen = left or right
    return (chosen.get("offset") if chosen.get("offset") is not None else 10**9,
            0 if left else 1)


def render(item: dict) -> str:
    return f"{item['at']} {item['speaker']}: {item['text']}"


def merge(sources: dict[str, str]) -> dict:
    """One merged transcript text plus the decision log clause 5 is proven from.

    `sources` maps the seam's source name ('meet'/'tactiq') to its decoded text.
    A single source merges to itself — there is nothing to cross-reference.
    """
    if not sources:
        refuse("no source text to merge", "pass at least one source")
    if "meet" not in sources or "tactiq" not in sources:
        only = next(iter(sources))
        items = utterances(sources[only])
        return {"text": sources[only], "sources": sorted(sources),
                "utterances": len(items), "compared": 0, "differing": 0,
                "meet-wins": 0, "tactiq-only": 0, "meet-only": 0, "decisions": []}

    meet = offsets(utterances(sources["meet"]))
    tactiq = offsets(utterances(sources["tactiq"]))
    lines, decisions = [], []
    compared = differing = meet_wins = tactiq_only = meet_only = 0
    for pair in align(meet, tactiq):
        left, right = pair["meet"], pair["tactiq"]
        if left is not None and right is not None:
            compared += 1
            if same_wording(left["text"], right["text"]):
                lines.append(render(left))
                continue
            differing += 1
            meet_wins += 1
            lines.append(render(left))
            decisions.append({"offset": left["offset"], "speaker": left["speaker"],
                              "won": "meet", "meet": left["text"], "tactiq": right["text"]})
        elif left is not None:
            meet_only += 1
            lines.append(render(left))
        else:
            tactiq_only += 1
            lines.append(render(right))
    return {"text": "\n".join(lines) + ("\n" if lines else ""),
            "sources": sorted(sources), "utterances": len(lines), "compared": compared,
            "differing": differing, "meet-wins": meet_wins,
            "tactiq-only": tactiq_only, "meet-only": meet_only, "decisions": decisions}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcript_merge",
        description="Cross-reference one meeting's transcripts into ONE text, Meet wording "
                    "winning every utterance where the two sources differ (goal.md clause 5).")
    parser.add_argument("--meet", type=Path, help="the Meet transcript file")
    parser.add_argument("--tactiq", type=Path, help="the Tactiq transcript file")
    parser.add_argument("--out", type=Path, help="write the merged text here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = {name: path.read_text(encoding="utf-8")
               for name, path in (("meet", args.meet), ("tactiq", args.tactiq)) if path}
    result = merge(sources)
    if args.out:
        args.out.write_text(result["text"], encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "text"},
                     ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
