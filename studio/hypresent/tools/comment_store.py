"""Shared comment parsing and digest rendering for hypresent lean views.

The source file's raw ``#hyp-comments`` JSON island is not copied into lean
views. It is represented through a lossless digest instead, so read/search
tools can inspect every persisted comment field without loading the visual page.

Gate-3 contract: the lean view drops the raw island; the digest is the ONLY
comment surface and MUST be lossless. Every island field is represented EXACTLY
ONCE — no field appears in both a readable element and a digest attribute. Human
fields (id, resolved state, author, body, contextText, replies) render as
readable text; machine fields (createdAt, editedAt, agentInstruction, anchor,
extra keys) render into typed attributes. Each value carries a reversible type
tag and is emitted ONLY when its key is present, so absent / null / typed values
round-trip byte-identically to the source JSON. Any thread the digest cannot
reproduce exactly is caught by ``dehydrate.verify``, which refuses the transform
(non-zero exit, no output file) rather than ship a lossy lean view — data is
never silently lost. (A size-driven never-grow fallback to the source island is
a separate path, triggered only when the composed lean would otherwise grow.)

The digest's machine attributes use compact bare names (``th``, ``ca``, ``ah`` …):
the digest is parsed only by ``extract_digest_threads`` in this module, never a
live page, so the ``data-`` prefix is dropped to keep the lean view small.

NOT FOR DESIGN WORK: lean views remove styling, scripts, and other visual layer
content that design changes require.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any

ISLAND_ID = "hyp-comments"
DIGEST_ID = "hyp-comment-digest"
AGENT_SENTINEL = "HYPRESENT AGENT INSTRUCTIONS"
THREAD_FIELDS = {
    "id",
    "anchor",
    "contextText",
    "author",
    "createdAt",
    "editedAt",
    "body",
    "resolved",
    "replies",
    "agentInstruction",
}
ANCHOR_FIELDS = ("hook", "path", "nativeId", "contentHash", "siblingIndex")

# Compact digest attribute names (bare, not ``data-*``).
_A_THREAD = "th"
_A_RESOLVED = "r"
_A_CREATED = "ca"
_A_EDITED = "ea"
_A_AGENT = "ai"
_A_ANCHOR = "anc"
_A_AXTRA = "ax"
_A_REPLIES = "rl"
_A_REPLY_TYPED = "rt"
_A_EXTRA_KEY = "ek"
_A_REPLY_KEY = "k"
_A_TYPE = "t"
# Known anchor keys mapped to their compact attribute names.
_ANCHOR_ATTRS = {
    "hook": "ah",
    "path": "ap",
    "nativeId": "an",
    "contentHash": "ac",
    "siblingIndex": "as",
}

# Sentinel distinguishing "key absent from source" from "key present with a
# value of None". Never compared for value equality — only identity.
_ABSENT = object()


class CommentStoreError(ValueError):
    """Raised when the persisted comment island exists but cannot be read."""


@dataclass(frozen=True)
class CommentStore:
    """Parsed-tree view of the persisted hypresent comment island."""

    raw_json: str | None
    threads: list[dict[str, Any]]

    @classmethod
    def from_soup(cls, soup: Any) -> "CommentStore":
        tag = soup.find("script", attrs={"id": ISLAND_ID})
        if tag is None:
            return cls(raw_json=None, threads=[])
        raw_json = tag.get_text()
        stripped = raw_json.strip()
        if not stripped:
            return cls(raw_json=raw_json, threads=[])
        try:
            parsed = json.loads(stripped)
        except Exception as exc:
            raise CommentStoreError(
                "source #hyp-comments island is present but its JSON does not parse"
            ) from exc
        if not isinstance(parsed, list):
            raise CommentStoreError("source #hyp-comments island must contain a JSON array")
        return cls(raw_json=raw_json, threads=parsed)

    @property
    def count(self) -> int:
        return len(self.threads)

    @property
    def open_count(self) -> int:
        return sum(1 for thread in self.threads if not thread.get("resolved"))

    @property
    def resolved_count(self) -> int:
        return self.count - self.open_count

    def suggested_selector(self, thread: dict[str, Any]) -> str | None:
        return suggested_selector(thread.get("anchor"))

    def render_digest_html(self) -> str:
        out = [
            f'<section id="{DIGEST_ID}" data-hyp-digest="lossless">',
            (
                f"<h1>Hypresent comment digest - {self.count} comment(s): "
                f"{self.open_count} open / {self.resolved_count} resolved</h1>"
            ),
            (
                "<p>The source #hyp-comments JSON island is represented here as "
                "a lossless digest. Use the full source file for edits.</p>"
            ),
        ]
        if not self.threads:
            out.append("<p>No comments in this file.</p>")
        else:
            out.append("<ol>")
            for thread in self.threads:
                out.extend(self._render_thread(thread))
            out.append("</ol>")
        out.append("</section>")
        return "\n".join(out)

    def _render_thread(self, thread: dict[str, Any]) -> list[str]:
        # Machine-channel attributes on the thread <li>. Each is emitted only
        # when its key is present in the source thread; presence therefore
        # round-trips (attribute missing == key absent).
        attrs: list[str] = [f'{_A_THREAD}="1"']
        for key, name in (
            ("resolved", _A_RESOLVED),
            ("createdAt", _A_CREATED),
            ("editedAt", _A_EDITED),
            ("agentInstruction", _A_AGENT),
        ):
            if key in thread:
                attrs.append(f'{name}="{_enc_attr(thread[key])}"')
        attrs.extend(self._render_anchor_attrs(thread))

        state = "resolved" if thread.get("resolved") else "open"

        # Human-readable header: id + state + author, each rendered once and
        # extractable. suggested_selector stays available for read/search
        # consumers but is not rendered inline (it is derived, not an island
        # field, and re-derivable from the retained anchor attributes).
        header = ['<p class="hd">', _render_inline("b", thread, "id", cls="i"), f" {state}"]
        if "author" in thread:
            header.append(" by ")
            header.append(_render_inline("cite", thread, "author"))
        header.append("</p>")

        rows = [f"<li {' '.join(attrs)}>", "".join(header)]
        rows.append(_render_block("blockquote", thread, "body"))
        rows.append(_render_block("p", thread, "contextText", cls="ctx"))

        for key in sorted(set(thread) - THREAD_FIELDS):
            rows.append(_extra_row(key, thread[key]))

        if "replies" in thread:
            rows.extend(self._render_replies(thread["replies"]))
        rows.append("</li>")
        return [row for row in rows if row]

    def _render_anchor_attrs(self, thread: dict[str, Any]) -> list[str]:
        if "anchor" not in thread:
            return []
        anchor = thread["anchor"]
        if not isinstance(anchor, dict):
            # null or scalar anchor: store the whole value, typed.
            return [f'{_A_ANCHOR}="{_enc_attr(anchor)}"']
        # Known-key presence is carried by whether its attribute exists, so no
        # separate key-list attribute is needed. Non-standard keys go to axtra.
        out = [f'{_A_ANCHOR}="{_attr("d")}"']
        extras: dict[str, Any] = {}
        for key, value in anchor.items():
            if key in _ANCHOR_ATTRS:
                out.append(f'{_ANCHOR_ATTRS[key]}="{_enc_attr(value)}"')
            else:
                extras[key] = value
        if extras:
            out.append(f'{_A_AXTRA}="{_attr(canonical_json(extras))}"')
        return out

    def _render_replies(self, replies: Any) -> list[str]:
        if not isinstance(replies, list):
            # non-list replies value: store typed on the marker element.
            return [f'<ol {_A_REPLIES}="{_enc_attr(replies)}"></ol>']
        rows = [f'<ol {_A_REPLIES}="l">']
        for reply in replies:
            if not isinstance(reply, dict):
                rows.append(f'<li {_A_REPLY_TYPED}="{_enc_attr(reply)}"></li>')
                continue
            rows.append("<li>")
            if "author" in reply:
                rows.append(_render_inline("cite", reply, "author"))
            if "body" in reply:
                rows.append(_render_inline("q", reply, "body"))
            if "createdAt" in reply:
                rows.append(_render_inline("time", reply, "createdAt"))
            for key in reply:
                if key in {"author", "body", "createdAt"}:
                    continue
                rows.append(
                    f'<span {_A_REPLY_KEY}="{html.escape(str(key), quote=True)}" '
                    f'{_A_TYPE}="{_type_tag(reply[key])}">{_type_text(reply[key])}</span>'
                )
            rows.append("</li>")
        rows.append("</ol>")
        return rows


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def suggested_selector(anchor: Any) -> str | None:
    """Return the anchor's native-id/path selector, or None when unanchored."""

    if not isinstance(anchor, dict):
        return None
    native_id = anchor.get("nativeId")
    if not native_id:
        return None
    selector = "#" + str(native_id)
    path = anchor.get("path") or ""
    for segment in [part for part in str(path).split("/") if part]:
        tag, _, nth = segment.partition(":")
        selector += f" > {tag}:nth-of-type({nth or '1'})"
    return selector


def extract_digest_threads(soup: Any) -> list[dict[str, Any]] | None:
    digest = soup.find(attrs={"id": DIGEST_ID})
    if digest is None:
        return None
    threads = []
    for item in digest.find_all(attrs={_A_THREAD: "1"}):
        if item.find_parent("ol", attrs={_A_REPLIES: True}) is not None:
            continue
        thread: dict[str, Any] = {}

        header = item.find("p", attrs={"class": "hd"}, recursive=False)
        _read_into(thread, "id", header.find("b", attrs={"class": "i"}) if header else None)
        _read_into(thread, "author", header.find("cite") if header else None)

        anchor = _read_anchor(item)
        if anchor is not _ABSENT:
            thread["anchor"] = anchor
        _read_attr_into(thread, "resolved", item, _A_RESOLVED)
        _read_attr_into(thread, "createdAt", item, _A_CREATED)
        _read_attr_into(thread, "editedAt", item, _A_EDITED)
        _read_attr_into(thread, "agentInstruction", item, _A_AGENT)

        _read_into(thread, "body", item.find("blockquote", recursive=False))
        _read_into(
            thread, "contextText", item.find("p", attrs={"class": "ctx"}, recursive=False)
        )

        for extra in item.find_all(attrs={_A_EXTRA_KEY: True}, recursive=False):
            thread[extra[_A_EXTRA_KEY]] = _dec_text(extra.get(_A_TYPE, "s"), extra.get_text())

        replies = _read_replies(item)
        if replies is not _ABSENT:
            thread["replies"] = replies
        threads.append(thread)
    return threads


# --- typed value codec ------------------------------------------------------
# Each scalar is stored as "<tag>:<text>" where tag in {s,n,b,i,f,j}. Presence
# is carried by whether the attribute/element exists at all, so the three JSON
# states absent / null / value are all distinguishable on read-back.

def _type_tag(value: Any) -> str:
    if value is None:
        return "n"
    if isinstance(value, bool):
        return "b"
    if isinstance(value, int):
        return "i"
    if isinstance(value, float):
        return "f"
    if isinstance(value, str):
        return "s"
    return "j"


def _type_text(value: Any) -> str:
    """Text payload for a value (no type tag). In text position, so escape only
    <, > and & — leaving quotes/apostrophes literal keeps prose from ballooning
    into &quot;/&#x27; entities."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return html.escape(repr(value) if isinstance(value, float) else str(value), quote=False)
    if isinstance(value, str):
        return html.escape(value, quote=False)
    return html.escape(canonical_json(value), quote=False)


def _enc_attr(value: Any) -> str:
    """Encode a value into a self-describing, HTML-attribute-safe string."""
    tag = _type_tag(value)
    if value is None:
        payload = ""
    elif isinstance(value, bool):
        payload = "true" if value else "false"
    elif isinstance(value, float):
        payload = repr(value)
    elif isinstance(value, (int, str)):
        payload = str(value)
    else:
        payload = canonical_json(value)
    return html.escape(f"{tag}:{payload}", quote=True)


def _dec_text(tag: str, text: str) -> Any:
    if tag == "n":
        return None
    if tag == "b":
        return text == "true"
    if tag == "i":
        return int(text)
    if tag == "f":
        return float(text)
    if tag == "j":
        return json.loads(text)
    return text


def _dec_attr(raw: str) -> Any:
    tag, _, payload = raw.partition(":")
    return _dec_text(tag, payload)


def _attr(value: str) -> str:
    return html.escape(value, quote=True)


# --- readable-element rendering / reading -----------------------------------

def _render_inline(tag: str, obj: dict[str, Any], key: str, cls: str | None = None) -> str:
    """Render obj[key] as inline readable text; type tag only when non-str."""
    value = obj[key]
    cls_attr = f' class="{cls}"' if cls else ""
    t = _type_tag(value)
    t_attr = "" if t == "s" else f' {_A_TYPE}="{t}"'
    return f"<{tag}{cls_attr}{t_attr}>{_type_text(value)}</{tag}>"


def _render_block(tag: str, obj: dict[str, Any], key: str, cls: str | None = None) -> str:
    if key not in obj:
        return ""
    return _render_inline(tag, obj, key, cls=cls)


def _read_into(thread: dict[str, Any], key: str, element: Any) -> None:
    if element is None:
        return
    thread[key] = _dec_text(element.get(_A_TYPE, "s"), element.get_text())


def _read_attr_into(thread: dict[str, Any], key: str, item: Any, attr: str) -> None:
    raw = item.get(attr)
    if raw is None:
        return
    thread[key] = _dec_attr(raw)


def _read_anchor(item: Any) -> Any:
    raw = item.get(_A_ANCHOR)
    if raw is None:
        return _ABSENT
    if raw != "d":
        return _dec_attr(raw)
    anchor: dict[str, Any] = {}
    for key, attr in _ANCHOR_ATTRS.items():
        raw_value = item.get(attr)
        if raw_value is not None:
            anchor[key] = _dec_attr(raw_value)
    extra_raw = item.get(_A_AXTRA)
    if extra_raw:
        anchor.update(json.loads(extra_raw))
    return anchor


def _read_replies(item: Any) -> Any:
    holder = item.find("ol", attrs={_A_REPLIES: True}, recursive=False)
    if holder is None:
        return _ABSENT
    marker = holder.get(_A_REPLIES)
    if marker != "l":
        return _dec_attr(marker)
    replies: list[Any] = []
    for reply_item in holder.find_all("li", recursive=False):
        rt = reply_item.get(_A_REPLY_TYPED)
        if rt is not None:
            replies.append(_dec_attr(rt))
            continue
        reply: dict[str, Any] = {}
        _read_into(reply, "author", reply_item.find("cite", recursive=False))
        _read_into(reply, "body", reply_item.find("q", recursive=False))
        _read_into(reply, "createdAt", reply_item.find("time", recursive=False))
        for field in reply_item.find_all(attrs={_A_REPLY_KEY: True}, recursive=False):
            reply[field[_A_REPLY_KEY]] = _dec_text(field.get(_A_TYPE, "s"), field.get_text())
        replies.append(reply)
    return replies


def _extra_row(key: str, value: Any) -> str:
    tag = "j" if isinstance(value, (dict, list)) else _type_tag(value)
    text = html.escape(canonical_json(value), quote=False) if tag == "j" else _type_text(value)
    return (
        f'<p {_A_EXTRA_KEY}="{html.escape(str(key), quote=True)}" '
        f'{_A_TYPE}="{tag}">{text}</p>'
    )
