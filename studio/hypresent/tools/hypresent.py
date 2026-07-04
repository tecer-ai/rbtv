#!/usr/bin/env python3
"""Umbrella AX CLI for hypresent.

The dehydrate subcommand creates a lean read view. The source file's raw
``#hyp-comments`` JSON island is represented through a lossless digest instead
of being copied into the lean view. NOT FOR DESIGN WORK: lean views remove the
visual layer that color, type, spacing, layout, and image edits require.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from comment_store import (
        AGENT_SENTINEL,
        DIGEST_ID,
        ISLAND_ID,
        CommentStore,
        CommentStoreError,
        canonical_json,
        extract_digest_threads,
    )
except ImportError:  # pragma: no cover - supports package-style imports later.
    from .comment_store import (  # type: ignore
        AGENT_SENTINEL,
        DIGEST_ID,
        ISLAND_ID,
        CommentStore,
        CommentStoreError,
        canonical_json,
        extract_digest_threads,
    )

KEEP_ATTRS = {
    "id",
    "class",
    "data-hyp-agent",
    "data-hyp-hook",
    "data-hyp-cid",
    "href",
    "colspan",
    "rowspan",
    "scope",
}
SVG_PLACEHOLDER = "[svg]"


class DehydrateError(RuntimeError):
    pass


def _load_bs4() -> tuple[Any, Any]:
    try:
        from bs4 import BeautifulSoup, Comment
    except ImportError as exc:
        raise DehydrateError(
            "beautifulsoup4 is not installed. Install it with: pip install beautifulsoup4 lxml"
        ) from exc
    return BeautifulSoup, Comment


def dehydrate(src_text: str) -> tuple[str, dict[str, Any]]:
    """Return ``(lean_html, stats)`` as a pure transform over source text."""

    BeautifulSoup, Comment = _load_bs4()
    soup = BeautifulSoup(src_text, "lxml")
    try:
        store = CommentStore.from_soup(soup)
    except CommentStoreError as exc:
        raise DehydrateError(str(exc)) from exc

    removed = {"style": 0, "svg": 0, "script": 0, "link": 0, "meta": 0, "noscript": 0}
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if AGENT_SENTINEL not in comment:
            comment.extract()

    for tag_name in ("style", "link", "noscript"):
        for tag in soup.find_all(tag_name):
            tag.decompose()
            removed[tag_name] += 1
    for tag in soup.find_all("svg"):
        tag.replace_with(SVG_PLACEHOLDER)
        removed["svg"] += 1
    for tag in soup.find_all("meta"):
        if tag.get("charset"):
            continue
        tag.decompose()
        removed["meta"] += 1
    for tag in soup.find_all("script"):
        tag.decompose()
        removed["script"] += 1

    for element in soup.find_all(True):
        for attr in list(element.attrs.keys()):
            if attr not in KEEP_ATTRS:
                del element.attrs[attr]

    digest_soup = BeautifulSoup(store.render_digest_html(), "lxml")
    digest = digest_soup.find(id=DIGEST_ID)
    if soup.body is not None and digest is not None:
        soup.body.insert(0, digest)
    elif digest is not None:
        soup.insert(0, digest)

    lean = str(soup)
    fallback = False
    if len(lean) > len(src_text) or len(lean.encode("utf-8")) > len(src_text.encode("utf-8")):
        lean = src_text
        fallback = True

    stats = {
        "src_chars": len(src_text),
        "lean_chars": len(lean),
        "src_bytes": len(src_text.encode("utf-8")),
        "lean_bytes": len(lean.encode("utf-8")),
        "comments_preserved": store.count,
        "agent_block_preserved": AGENT_SENTINEL not in src_text or AGENT_SENTINEL in lean,
        "fallback": fallback,
        "removed": removed,
    }
    stats["reduction_pct"] = (
        round((1 - stats["lean_bytes"] / stats["src_bytes"]) * 100, 1)
        if stats["src_bytes"]
        else 0.0
    )
    errors = verify(lean, src_text, fallback=fallback)
    if errors:
        raise DehydrateError("lean output failed verification: " + "; ".join(errors))
    return lean, stats


def verify(lean_html: str, src_text: str, fallback: bool = False) -> list[str]:
    BeautifulSoup, _ = _load_bs4()
    errors: list[str] = []
    try:
        source_store = CommentStore.from_soup(BeautifulSoup(src_text, "lxml"))
    except CommentStoreError as exc:
        return [str(exc)]

    lean_soup = BeautifulSoup(lean_html, "lxml")
    if fallback:
        try:
            fallback_store = CommentStore.from_soup(lean_soup)
        except CommentStoreError as exc:
            return [str(exc)]
        if canonical_json(fallback_store.threads) != canonical_json(source_store.threads):
            errors.append("fallback source island no longer matches the original comments")
    else:
        if lean_soup.find("script", attrs={"id": ISLAND_ID}) is not None:
            errors.append("lean view still contains the raw #hyp-comments island")
        try:
            digest_threads = extract_digest_threads(lean_soup)
        except Exception as exc:
            errors.append(f"lossless digest JSON does not parse: {exc}")
            digest_threads = None
        if digest_threads is None:
            errors.append("lean view is missing the lossless comment digest")
        elif canonical_json(digest_threads) != canonical_json(source_store.threads):
            errors.append("lossless digest does not match the source comment island")

    if AGENT_SENTINEL in src_text and AGENT_SENTINEL not in lean_html:
        errors.append("agent-instruction block present in source but missing from lean view")
    if len(lean_html) > len(src_text):
        errors.append("lean view grew in characters")
    if len(lean_html.encode("utf-8")) > len(src_text.encode("utf-8")):
        errors.append("lean view grew in bytes")
    return errors


def default_out_path(src: Path) -> Path:
    return src.with_name(src.stem + ".lean" + src.suffix)


def run_dehydrate(args: argparse.Namespace) -> int:
    source = Path(args.file)
    if not source.is_file():
        print(f"hypresent dehydrate: error: file not found: {source}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else default_out_path(source)
    try:
        src_text = source.read_text(encoding="utf-8")
        lean, stats = dehydrate(src_text)
    except DehydrateError as exc:
        message = str(exc)
        code = 3 if "beautifulsoup4 is not installed" in message else 2
        print(f"hypresent dehydrate: error: {message}", file=sys.stderr)
        return code
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(lean, encoding="utf-8")
    summary = {
        "ok": True,
        "file": os.fspath(source),
        "out": os.fspath(out),
        **stats,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "dehydrate: "
            f"{summary['src_bytes']} bytes -> {summary['lean_bytes']} bytes "
            f"({summary['reduction_pct']}% smaller; "
            f"{summary['src_chars']} chars -> {summary['lean_chars']} chars; "
            f"comments preserved: {summary['comments_preserved']}; "
            f"fallback: {str(summary['fallback']).lower()})"
        )
        print(f"  wrote: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hypresent.py",
        description=(
            "AX CLI for hypresent. Dehydrate creates lean read views whose "
            "#hyp-comments island is represented via a lossless digest. "
            "NOT FOR DESIGN WORK."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    dehydrate_parser = subparsers.add_parser(
        "dehydrate",
        help="Create a never-grow lean read view with a lossless comment digest.",
        description=(
            "Create a never-grow lean read view. The source #hyp-comments JSON "
            "island is represented via a lossless digest, not copied raw. "
            "NOT FOR DESIGN WORK."
        ),
    )
    dehydrate_parser.add_argument("--file", required=True, help="Source hypresent HTML file.")
    dehydrate_parser.add_argument("--out", help="Output path. Default: <file>.lean.html.")
    dehydrate_parser.add_argument("--json", action="store_true", help="Print JSON stats.")
    dehydrate_parser.set_defaults(func=run_dehydrate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
