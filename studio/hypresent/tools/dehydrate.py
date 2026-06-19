#!/usr/bin/env python3
"""dehydrate.py — produce a token-reduced "read view" of a saved hypresent file.

An agent that is READING a hypresent artifact — to read existing review comments,
to find an element to comment on, or to assess deck-wide impact before implementing
comments — does not need the visual layer (CSS, inline SVG, web fonts, vendor JS).
This tool strips that weight while PRESERVING everything the comment system needs,
so the agent works off a much smaller file and can still "comment back".

PRESERVED (never stripped):
  * the #hyp-comments JSON island (every comment thread) — re-injected byte-for-byte
  * the HYPRESENT AGENT INSTRUCTIONS head block (an HTML comment) — kept verbatim
  * selector hooks on every element: id, class, data-hyp-agent, and the FULL tag
    nesting (never collapsed). So any CSS selector an agent reads off the lean view
    resolves against the REAL file, and add_comment.py anchors it correctly. The
    comment anchor (nativeId + tag:nth path + content hash + sibling index) depends
    on exactly these survivors.

STRIPPED:
  * <style> blocks and every style="" attribute
  * inline <svg> (decorative)
  * vendor / runtime <script> (everything EXCEPT the JSON island)
  * <link> (stylesheets/fonts), <meta> (except charset), <noscript>
  * presentational / handler attributes (on*, width, height, fill, stroke, aria-*, …)

ADDED:
  * a readable comment digest at the top of <body> — per comment: id, author,
    open/resolved, agent-tagged?, the anchored element + a suggested unique CSS
    selector, the body, and replies — so existing comments read at a glance.

NOT FOR DESIGN WORK. A design change (color, type, size, spacing, layout, image)
operates on exactly the visual layer this tool removes. For design, read the FULL
file (or the full markup + CSS of the target element) — never the lean view.

Usage:
  python tools/dehydrate.py --file deck.html [--out deck.lean.html] [--json]

Exit 0 on success (prints a stats summary; --json prints machine-readable stats).
Non-zero with a clear message on failure (file not found, parse error, or a comment
store lost in the lean output — the tool refuses to emit a view that dropped comments).
"""
import argparse
import html as _html
import json
import os
import re
import sys

ISLAND_ID = "hyp-comments"
AGENT_SENTINEL = "HYPRESENT AGENT INSTRUCTIONS"

# Attributes kept on every element (besides the untouched island <script>).
# These are the selector + anchor survivors; everything else is visual noise.
KEEP_ATTRS = {
    "id", "class", "data-hyp-agent", "data-hyp-hook",
    "href", "colspan", "rowspan", "scope",
}

# Marker text inserted where an inline <svg> was removed, so structure stays legible.
SVG_PLACEHOLDER = "[svg]"


def _fail(msg, code=2):
    print(f"dehydrate: ERROR — {msg}", file=sys.stderr)
    sys.exit(code)


def island_from_soup(soup):
    """Return (raw_inner_json, parsed_list) for the REAL #hyp-comments island.

    Resolved through the PARSED tree, never a raw-text regex: a literal
    '<script … id="hyp-comments">' that appears as descriptive TEXT inside the
    agent-instructions HTML comment (the current agent block names the island tag
    in its preamble) is correctly ignored — only a genuine element matches.
    parsed_list is None if the island is absent or its JSON does not parse;
    raw_inner is None only if the island element is absent.
    """
    tag = soup.find("script", attrs={"id": ISLAND_ID})
    if tag is None:
        return None, None
    inner = tag.get_text()
    stripped = inner.strip()
    try:
        data = json.loads(stripped) if stripped else []
        if not isinstance(data, list):
            data = None
    except Exception:
        data = None
    return inner, data


def extract_agentblock_raw(src):
    """Return the raw <!-- … HYPRESENT AGENT INSTRUCTIONS … --> comment, or None."""
    m = re.search(r'<!--\s*=+\s*%s.*?-->' % re.escape(AGENT_SENTINEL), src, re.S)
    return m.group(0) if m else None


def _suggested_selector(anchor):
    """Best-effort unique CSS selector from a comment anchor.

    The anchor path is a chain of direct-child `tag:nth` steps (nth among same-tag
    siblings, 1-based) under the nearest native-id ancestor — which maps exactly to
    `#nativeId > tag:nth-of-type(n) > …`. Returns None when the anchor lacks a
    native-id base (the agent then crafts a selector by reading the lean markup).
    """
    if not isinstance(anchor, dict):
        return None
    native_id = anchor.get("nativeId")
    if not native_id:
        return None
    sel = "#" + native_id
    path = anchor.get("path") or ""
    for seg in [s for s in path.split("/") if s]:
        tag, _, nth = seg.partition(":")
        nth = nth or "1"
        sel += f" > {tag}:nth-of-type({nth})"
    return sel


def build_digest_html(comments):
    """Render the readable comment digest as an HTML string."""
    n = len(comments)
    n_open = sum(1 for c in comments if not c.get("resolved"))
    n_res = n - n_open
    out = ['<section id="hyp-comment-digest" data-hyp-digest="true">']
    out.append(
        f"<h1>Hypresent comment digest — {n} comment(s): {n_open} open / {n_res} resolved</h1>"
    )
    if not comments:
        out.append("<p>No comments in this file.</p></section>")
        return "\n".join(out)
    out.append("<ol>")
    for c in comments:
        cid = _html.escape(str(c.get("id", "?")))
        state = "RESOLVED" if c.get("resolved") else "OPEN"
        agent = " [AGENT-TAGGED]" if c.get("agentInstruction") else ""
        author = _html.escape(str(c.get("author", "")))
        ctx = _html.escape(str(c.get("contextText", "")))
        body = _html.escape(str(c.get("body", "")))
        anchor = c.get("anchor") or {}
        native = anchor.get("nativeId") if isinstance(anchor, dict) else None
        path = anchor.get("path") if isinstance(anchor, dict) else None
        sel = _suggested_selector(anchor)
        loc = (
            f'element <code>#{_html.escape(str(native))}</code> path <code>{_html.escape(str(path))}</code>'
            if native else "<em>unanchored / no native-id base — craft a selector from the markup below</em>"
        )
        sel_html = f' — suggested selector <code>{_html.escape(sel)}</code>' if sel else ""
        out.append(f'<li id="hyp-digest-{cid}">')
        out.append(f"<strong>#{cid}</strong> [{state}]{agent} by {author}<br>")
        out.append(f"{loc}{sel_html}<br>")
        out.append(f'context: "{ctx}"<br>')
        out.append(f"comment: {body}")
        replies = c.get("replies") or []
        if replies:
            out.append("<ul>")
            for r in replies:
                ra = _html.escape(str(r.get("author", "")))
                rb = _html.escape(str(r.get("body", "")))
                out.append(f"<li>reply by {ra}: {rb}</li>")
            out.append("</ul>")
        out.append("</li>")
    out.append("</ol></section>")
    return "\n".join(out)


def dehydrate(src_text):
    """Return (lean_html_str, stats_dict). Pure function over the source text."""
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(src_text, "lxml")
    island_raw, comments = island_from_soup(soup)
    agentblock_raw = extract_agentblock_raw(src_text)
    comments = comments or []

    # --- Remove non-comment HTML comments; keep the agent-instruction block ---
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if AGENT_SENTINEL not in c:
            c.extract()

    # --- Drop the visual / behavioural layer ---
    removed = {"style": 0, "svg": 0, "script": 0, "link": 0, "meta": 0, "noscript": 0}
    for tag in soup.find_all("style"):
        tag.decompose(); removed["style"] += 1
    for tag in soup.find_all("svg"):
        tag.replace_with(SVG_PLACEHOLDER); removed["svg"] += 1
    for tag in soup.find_all("link"):
        tag.decompose(); removed["link"] += 1
    for tag in soup.find_all("noscript"):
        tag.decompose(); removed["noscript"] += 1
    for tag in soup.find_all("meta"):
        if tag.get("charset"):
            continue
        tag.decompose(); removed["meta"] += 1
    # Scripts: drop everything EXCEPT the JSON island (id=hyp-comments).
    for tag in soup.find_all("script"):
        if (tag.get("id") or "").strip() == ISLAND_ID:
            continue
        tag.decompose(); removed["script"] += 1

    # --- Strip noise attributes from every surviving element (island untouched) ---
    for el in soup.find_all(True):
        if el.name == "script" and (el.get("id") or "").strip() == ISLAND_ID:
            continue
        for attr in list(el.attrs.keys()):
            if attr not in KEEP_ATTRS:
                del el[attr]

    # --- Prepend the readable comment digest to <body> ---
    digest_soup = BeautifulSoup(build_digest_html(comments), "lxml")
    digest_node = digest_soup.find(id="hyp-comment-digest")
    body = soup.body
    if body is not None and digest_node is not None:
        body.insert(0, digest_node)

    # bs4 leaves the untouched island <script> content as-is (script text is not
    # entity-escaped on output), so no raw re-injection is needed. verify() re-parses
    # the result and fails loud if the island's comments did not survive intact.
    lean = str(soup)

    stats = {
        "src_bytes": len(src_text.encode("utf-8")),
        "lean_bytes": len(lean.encode("utf-8")),
        "comments": len(comments),
        "sections": len(soup.find_all("section")) - (1 if comments is not None else 0),
        "agent_block_in_source": agentblock_raw is not None,
        "removed": removed,
    }
    return lean, stats


def verify(lean_html, src_text):
    """Confirm the lean output kept both comment stores intact. Returns list of errors."""
    from bs4 import BeautifulSoup
    errors = []
    src_raw, src_comments = island_from_soup(BeautifulSoup(src_text, "lxml"))
    lean_raw, lean_comments = island_from_soup(BeautifulSoup(lean_html, "lxml"))

    if src_raw is not None and src_comments is None:
        errors.append("source #hyp-comments island is present but its JSON does not parse — "
                      "refusing to emit (cannot prove the comments survived)")
    if src_raw is not None and lean_raw is None:
        errors.append("#hyp-comments island present in source but missing from the lean output")
    if src_comments is not None and lean_comments != src_comments:
        ln = len(lean_comments) if lean_comments is not None else "missing/unparseable"
        errors.append(f"island comments changed: source {len(src_comments)} -> lean {ln}")
    if AGENT_SENTINEL in src_text and AGENT_SENTINEL not in lean_html:
        errors.append("agent-instruction block present in source but dropped from the lean output")
    return errors


def main():
    ap = argparse.ArgumentParser(
        description="Produce a token-reduced read view of a saved hypresent file."
    )
    ap.add_argument("--file", required=True, help="Path to the saved hypresent HTML.")
    ap.add_argument("--out", default=None,
                    help="Output path. Default: '<file>.lean.html' next to the source.")
    ap.add_argument("--json", action="store_true", help="Print machine-readable stats.")
    args = ap.parse_args()

    src = os.path.abspath(args.file)
    if not os.path.isfile(src):
        _fail(f"file not found: {src}")
    out = os.path.abspath(args.out) if args.out else (
        os.path.splitext(src)[0] + ".lean.html"
    )

    try:
        from bs4 import BeautifulSoup  # noqa: F401
    except ImportError:
        _fail("beautifulsoup4 is not installed in this environment.", code=3)

    text = open(src, encoding="utf-8").read()
    lean, stats = dehydrate(text)

    errors = verify(lean, text)
    if errors:
        _fail("lean output lost a comment store — refusing to write:\n  - " + "\n  - ".join(errors))

    with open(out, "w", encoding="utf-8") as f:
        f.write(lean)

    pct = (1 - stats["lean_bytes"] / stats["src_bytes"]) * 100 if stats["src_bytes"] else 0
    est_tok_src = stats["src_bytes"] // 4
    est_tok_lean = stats["lean_bytes"] // 4
    summary = {
        "ok": True,
        "file": src,
        "out": out,
        "src_kb": round(stats["src_bytes"] / 1024, 1),
        "lean_kb": round(stats["lean_bytes"] / 1024, 1),
        "reduction_pct": round(pct, 1),
        "est_tokens_src": est_tok_src,
        "est_tokens_lean": est_tok_lean,
        "comments_preserved": stats["comments"],
        "agent_block_preserved": stats["agent_block_in_source"],
        "removed": stats["removed"],
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"dehydrate: {summary['src_kb']} KB -> {summary['lean_kb']} KB "
              f"({summary['reduction_pct']}% smaller; ~{est_tok_src} -> ~{est_tok_lean} est. tokens)")
        print(f"  comments preserved: {summary['comments_preserved']}  "
              f"agent block preserved: {summary['agent_block_preserved']}")
        print(f"  removed: {summary['removed']}")
        print(f"  wrote: {out}")


if __name__ == "__main__":
    main()
