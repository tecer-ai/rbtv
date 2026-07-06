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
    from deck_query import DeckQuery, DeckQueryDependencyError, DeckQueryError, render_human
    from deck_session import DeckSessionError, add_comment, reply
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
    from .deck_query import (  # type: ignore
        DeckQuery,
        DeckQueryDependencyError,
        DeckQueryError,
        render_human,
    )
    from .deck_session import DeckSessionError, add_comment, reply  # type: ignore

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
        with source.open(encoding="utf-8", newline="") as f:
            src_text = f.read()
        lean, stats = dehydrate(src_text)
    except DehydrateError as exc:
        message = str(exc)
        code = 3 if "beautifulsoup4 is not installed" in message else 2
        print(f"hypresent dehydrate: error: {message}", file=sys.stderr)
        return code
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(lean, encoding="utf-8", newline="")
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


def _load_query(args: argparse.Namespace, command: str) -> tuple[DeckQuery | None, int]:
    try:
        return DeckQuery(Path(args.file)), 0
    except DeckQueryDependencyError as exc:
        print(f"hypresent {command}: error: {exc}", file=sys.stderr)
        return None, 3
    except DeckQueryError as exc:
        print(f"hypresent {command}: error: {exc}", file=sys.stderr)
        return None, 2


def run_read(args: argparse.Namespace) -> int:
    query, error_code = _load_query(args, "read")
    if query is None:
        return error_code
    try:
        if args.selector:
            payload = query.read_selector(args.selector, include_line_numbers=args.line_numbers)
        elif args.comment:
            relation = "self" if args.self else "parent" if args.parent else "sibling" if args.sibling else ""
            if relation:
                payload = query.read_comment_element(
                    args.comment, relation, include_line_numbers=args.line_numbers
                )
            else:
                payload = query.read_thread(args.comment)
        elif args.mode == "corpus":
            payload = query.read_corpus()
        elif args.mode == "doc":
            payload = query.read_doc(state=args.state, agent=args.agent)
        else:
            payload = query.read_comments(state=args.state, agent=args.agent)
    except DeckQueryError as exc:
        print(f"hypresent read: error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(render_human(payload, include_line_numbers=args.line_numbers))
    return 0


def run_search(args: argparse.Namespace) -> int:
    query, error_code = _load_query(args, "search")
    if query is None:
        return error_code
    payload = query.search(args.query, case_sensitive=args.case_sensitive)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(render_human(payload, include_line_numbers=True))
    return 0


def run_add_comment(args: argparse.Namespace) -> int:
    try:
        payload = add_comment(args.file, args.selector, args.body, args.author, args.agent, args.out)
    except DeckSessionError as exc:
        print(f"hypresent add-comment: ERROR — {exc}", file=sys.stderr)
        return exc.code
    print(json.dumps(payload, indent=2))
    return 0


def run_reply(args: argparse.Namespace) -> int:
    try:
        payload = reply(
            args.file,
            args.comment_id,
            args.reply,
            args.author,
            args.set_agent,
            args.clear_agent,
            args.out,
        )
    except DeckSessionError as exc:
        print(f"hypresent reply: ERROR — {exc}", file=sys.stderr)
        return exc.code
    print(json.dumps(payload, indent=2))
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

    read_parser = subparsers.add_parser(
        "read",
        help="Read saved-deck comments or page elements without a browser.",
        description=(
            "Read a saved hypresent HTML file. Default mode is comments. "
            "Use --comment for one thread, --self/--parent/--sibling for its "
            "data-hyp-cid element context, or --selector for a one-off CSS selector."
        ),
    )
    read_parser.add_argument("--file", required=True, help="Saved hypresent HTML file.")
    read_parser.add_argument(
        "--mode",
        choices=["comments", "corpus", "doc"],
        default="comments",
        help="Read mode. Default: comments. comments prints threads; corpus prints page text only; doc prints both.",
    )
    read_parser.add_argument(
        "--state",
        choices=["all", "open", "resolved"],
        default="all",
        help="Thread state filter for comments/doc modes. Default: all.",
    )
    read_parser.add_argument(
        "--agent",
        choices=["any", "with", "without"],
        default="any",
        help="Thread agentInstruction filter for comments/doc modes. Default: any.",
    )
    read_parser.add_argument("--comment", help="Read one comment thread by id.")
    relation = read_parser.add_mutually_exclusive_group()
    relation.add_argument(
        "--self",
        action="store_true",
        help="With --comment, print element(s) whose data-hyp-cid token matches the comment id.",
    )
    relation.add_argument(
        "--parent",
        action="store_true",
        help="With --comment, print parent element(s) of matching data-hyp-cid element(s).",
    )
    relation.add_argument(
        "--sibling",
        action="store_true",
        help="With --comment, print sibling element(s) of matching data-hyp-cid element(s).",
    )
    read_parser.add_argument(
        "--selector",
        help="CSS selector for stateless element reads not tied to a comment. Zero matches exit 0.",
    )
    read_parser.add_argument(
        "--line-numbers",
        action="store_true",
        help="Include source line numbers when available. Default: omitted from human labels.",
    )
    read_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    read_parser.set_defaults(func=run_read)

    search_parser = subparsers.add_parser(
        "search",
        help="Plain term search over saved-deck page text without a browser.",
        description=(
            "Search page text in a saved hypresent HTML file. Search is "
            "case-insensitive by default and returns snippets with location context."
        ),
    )
    search_parser.add_argument("--file", required=True, help="Saved hypresent HTML file.")
    search_parser.add_argument("--query", required=True, help="Plain text term to find.")
    search_parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Make search case-sensitive. Default: false, search is case-insensitive.",
    )
    search_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    search_parser.set_defaults(func=run_search)

    add_parser = subparsers.add_parser(
        "add-comment",
        help="Add a review comment through the real hypresent runtime.",
        description="Add a hypresent review comment by driving the real app and saving through its save handler.",
    )
    add_parser.add_argument("--file", required=True, help="Path to the HTML deck to comment on.")
    add_parser.add_argument(
        "--selector",
        required=True,
        help="CSS selector for the target element; it must match exactly one deck element.",
    )
    add_parser.add_argument("--body", required=True, help="Comment body text.")
    add_parser.add_argument(
        "--author",
        default="Agent",
        help="Comment author identity. Default: Agent.",
    )
    add_parser.add_argument(
        "--agent",
        action="store_true",
        help="Mark the comment as an agent instruction. Default: false.",
    )
    add_parser.add_argument(
        "--out",
        default=None,
        help="Optional output path. Default: save in place and overwrite --file.",
    )
    add_parser.set_defaults(func=run_add_comment)

    reply_parser = subparsers.add_parser(
        "reply",
        help="Reply to a comment thread or toggle its agent-instruction flag.",
        description=(
            "Reply to an existing hypresent comment thread and/or set or clear "
            "its agent-instruction flag through the real runtime."
        ),
    )
    reply_parser.add_argument("--file", required=True, help="Path to the HTML deck.")
    reply_parser.add_argument("--comment-id", required=True, help="Existing comment thread id.")
    reply_parser.add_argument("--reply", default=None, help="Reply body text to append to the thread.")
    reply_parser.add_argument("--author", default="Agent", help="Author identity for the reply. Default: Agent.")
    agent_group = reply_parser.add_mutually_exclusive_group()
    agent_group.add_argument("--set-agent", action="store_true", help="Tag the thread as an agent instruction.")
    agent_group.add_argument("--clear-agent", action="store_true", help="Remove the agent-instruction tag.")
    reply_parser.add_argument(
        "--out",
        default=None,
        help="Optional output path. Default: save in place and overwrite --file.",
    )
    reply_parser.set_defaults(func=run_reply)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
