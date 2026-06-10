"""Pure recompose engine — byte-range section splicing, stdlib only."""

BLANK_SECTION = (
    '<section class="slide">\n'
    "    <h2>Blank Slide</h2>\n"
    "</section>\n"
)


class RecomposeError(ValueError):
    """Raised when recompose constraints are violated."""


def split_sections(html: str) -> list[tuple[int, int]]:
    """Return byte spans (start, end) of each top-level <section>…</section>.

    Depth-counts nested <section> tags and ignores tags inside HTML comments.
    """
    spans: list[tuple[int, int]] = []
    depth = 0
    in_comment = False
    i = 0
    n = len(html)
    current_start: int | None = None

    while i < n:
        if not in_comment:
            if html.startswith("<!--", i):
                in_comment = True
                i += 4
                continue
        else:
            if html.startswith("-->", i):
                in_comment = False
                i += 3
                continue
            i += 1
            continue

        # Not in a comment — look for section tags.
        if html.startswith("<section", i):
            after = i + 8
            if after < n and html[after] in " \t\n>":
                if depth == 0:
                    current_start = i
                depth += 1
                i += 8
                continue

        if html.startswith("</section>", i):
            depth -= 1
            if depth < 0:
                raise RecomposeError("Unexpected </section> — unbalanced tags")
            if depth == 0 and current_start is not None:
                spans.append((current_start, i + 10))
                current_start = None
            i += 10
            continue

        i += 1

    if depth != 0:
        raise RecomposeError("Unbalanced <section> tags")

    return spans


def recompose(html: str, items: list[dict]) -> str:
    """Rebuild document preserving inter-slide separators.

    Output = prefix + item₀ + sep(item₀) + item₁ + sep(item₁) + … +
             itemₙ₋₁ + suffix  (no separator after the last item).

    Each item is a dict:
      - {"kind": "existing", "index": int}  → copy Nth section verbatim
      - {"kind": "fragment", "html": str}   → insert html as-is
      - {"kind": "blank"}                   → insert BLANK_SECTION
    """
    spans = split_sections(html)
    if not spans:
        raise RecomposeError("no <section> slides found — not a conforming deck")

    prefix = html[: spans[0][0]]
    suffix = html[spans[-1][1] :]

    # Source separators: sep[i] is the text between section i and i+1.
    separators: list[str] = []
    for i in range(len(spans) - 1):
        separators.append(html[spans[i][1] : spans[i + 1][0]])

    # Default separator: most common, tie → first in document order.
    # "\n" when the deck has fewer than 2 sections (no separators exist).
    if len(separators) == 0:
        default_sep = "\n"
    else:
        from collections import Counter

        counts = Counter(separators)
        max_count = max(counts.values())
        default_sep = next(sep for sep in separators if counts[sep] == max_count)

    def _sep_for(item: dict) -> str:
        """Return the separator that follows *item*."""
        if item.get("kind") == "existing":
            idx = item["index"]
            if idx < len(spans) - 1:
                return separators[idx]
        return default_sep

    parts: list[str] = [prefix]
    last_idx = len(items) - 1
    for pos, item in enumerate(items):
        kind = item.get("kind")
        if kind == "existing":
            if "index" not in item:
                raise RecomposeError("existing item missing 'index'")
            idx = item["index"]
            if not isinstance(idx, int) or idx < 0 or idx >= len(spans):
                raise RecomposeError(
                    f"section index {idx} out of range (0-{len(spans) - 1})"
                )
            start, end = spans[idx]
            parts.append(html[start:end])
        elif kind == "fragment":
            if "html" not in item:
                raise RecomposeError("fragment item missing 'html'")
            parts.append(item["html"])
        elif kind == "blank":
            parts.append(BLANK_SECTION)
        else:
            raise RecomposeError(f"unknown item kind: {kind}")

        # Separator between items, none after the last item.
        if pos < last_idx:
            parts.append(_sep_for(item))

    parts.append(suffix)
    return "".join(parts)
