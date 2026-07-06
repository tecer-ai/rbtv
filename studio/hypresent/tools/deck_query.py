"""Read-only query helpers for saved hypresent decks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from comment_store import CommentStore, CommentStoreError
except ImportError:  # pragma: no cover - supports package-style imports later.
    from .comment_store import CommentStore, CommentStoreError  # type: ignore


class DeckQueryError(RuntimeError):
    """Raised when a saved deck cannot be queried."""


class DeckQueryDependencyError(DeckQueryError):
    """Raised when the HTML parser dependency is missing."""


def _load_bs4() -> Any:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise DeckQueryDependencyError(
            "beautifulsoup4 is not installed. Install it with: pip install beautifulsoup4 lxml"
        ) from exc
    return BeautifulSoup


class DeckQuery:
    """Parsed saved-deck view used by the CLI read/search commands."""

    def __init__(self, path: Path) -> None:
        if not path.is_file():
            raise DeckQueryError(f"file not found: {path}")
        self.path = path
        self.source = path.read_text(encoding="utf-8")
        BeautifulSoup = _load_bs4()
        self.soup = BeautifulSoup(self.source, "lxml")
        try:
            self.store = CommentStore.from_soup(self.soup)
        except CommentStoreError as exc:
            raise DeckQueryError(str(exc)) from exc
        self._threads_by_id = {
            str(thread.get("id")): thread for thread in self.store.threads if "id" in thread
        }

    @property
    def available_ids(self) -> list[str]:
        return [str(thread.get("id")) for thread in self.store.threads if "id" in thread]

    def read_comments(self, state: str = "all", agent: str = "any") -> dict[str, Any]:
        threads = [thread for thread in self.store.threads if _thread_matches(thread, state, agent)]
        return {"kind": "comments", "count": len(threads), "threads": threads}

    def read_corpus(self) -> dict[str, Any]:
        return {"kind": "corpus", "text": self._corpus_text()}

    def read_doc(self, state: str = "all", agent: str = "any") -> dict[str, Any]:
        comments = self.read_comments(state=state, agent=agent)
        return {
            "kind": "doc",
            "count": comments["count"],
            "threads": comments["threads"],
            "corpus": self.read_corpus(),
        }

    def read_thread(self, comment_id: str) -> dict[str, Any]:
        thread = self._thread(comment_id)
        return {"kind": "comment", "thread": thread}

    def read_comment_element(
        self, comment_id: str, relation: str, include_line_numbers: bool = False
    ) -> dict[str, Any]:
        self._thread(comment_id)
        matches = self._cid_matches(comment_id)
        if not matches:
            return {
                "kind": "element",
                "status": "unanchored",
                "comment_id": comment_id,
                "relation": relation,
                "matches": [],
                "anomaly": None,
            }

        related = []
        for match in matches:
            related.extend(self._related_elements(match, relation))
        return {
            "kind": "element",
            "status": "ok",
            "comment_id": comment_id,
            "relation": relation,
            "matches": [self._element_record(element, include_line_numbers) for element in related],
            "anomaly": "multiple-elements" if len(matches) > 1 else None,
        }

    def read_selector(self, selector: str, include_line_numbers: bool = False) -> dict[str, Any]:
        try:
            matches = self.soup.select(selector)
        except Exception as exc:
            raise DeckQueryError(f"invalid selector: {selector} ({exc})") from exc
        return {
            "kind": "selector",
            "status": "ok" if matches else "empty",
            "selector": selector,
            "matches": [self._element_record(element, include_line_numbers) for element in matches],
            "anomaly": None,
        }

    def search(self, query: str, case_sensitive: bool = False) -> dict[str, Any]:
        needle = query if case_sensitive else query.lower()
        hits: list[dict[str, Any]] = []
        for node in self._corpus_text_nodes():
            text = str(node)
            haystack = text if case_sensitive else text.lower()
            start = 0
            while True:
                index = haystack.find(needle, start)
                if index == -1:
                    break
                parent = node.parent
                hits.append(
                    {
                        "snippet": _snippet(text, index, len(query)),
                        "line": self._line_for(parent),
                        "location": self._location(parent),
                    }
                )
                start = index + max(len(needle), 1)
        return {
            "kind": "search",
            "status": "ok" if hits else "empty",
            "query": query,
            "case_sensitive": case_sensitive,
            "count": len(hits),
            "hits": hits,
        }

    def _thread(self, comment_id: str) -> dict[str, Any]:
        thread = self._threads_by_id.get(comment_id)
        if thread is None:
            available = ", ".join(self.available_ids) if self.available_ids else "(none)"
            raise DeckQueryError(f"comment id not found: {comment_id}; available ids: {available}")
        return thread

    def _cid_matches(self, comment_id: str) -> list[Any]:
        selector = f'[data-hyp-cid~="{_css_string(comment_id)}"]'
        return list(self.soup.select(selector))

    def _related_elements(self, element: Any, relation: str) -> list[Any]:
        if relation == "self":
            return [element]
        if relation == "parent":
            return [element.parent] if getattr(element.parent, "name", None) else []
        siblings = []
        for sibling in element.find_previous_siblings():
            siblings.append(sibling)
        siblings.reverse()
        siblings.extend(element.find_next_siblings())
        return siblings

    def _element_record(self, element: Any, include_line_numbers: bool) -> dict[str, Any]:
        attrs = {key: _attr_value(value) for key, value in element.attrs.items()}
        line = self._line_for(element)
        return {
            "tag": element.name,
            "attrs": attrs,
            "line": line if include_line_numbers else None,
            "html": str(element),
            "location": self._location(element),
        }

    def _corpus_text(self) -> str:
        return "\n".join(text.strip() for text in self._corpus_text_nodes() if text.strip())

    def _corpus_text_nodes(self) -> list[Any]:
        root = self.soup.body or self.soup
        nodes = []
        for node in root.find_all(string=True):
            if not str(node).strip():
                continue
            if node.find_parent(["script", "style", "noscript", "template"]):
                continue
            nodes.append(node)
        return nodes

    def _location(self, element: Any) -> dict[str, Any]:
        nearest_id = None
        for parent in [element, *list(element.parents)]:
            if getattr(parent, "attrs", None) and parent.get("id"):
                nearest_id = parent.get("id")
                break
        class_chain = []
        for parent in reversed([element, *list(element.parents)]):
            if getattr(parent, "attrs", None) and parent.get("class"):
                class_chain.append("." + ".".join(parent.get("class")))
        comment_selector = None
        cid_owner = element.find_parent(attrs={"data-hyp-cid": True})
        if element.get("data-hyp-cid"):
            cid_owner = element
        if cid_owner is not None:
            for cid in str(cid_owner.get("data-hyp-cid", "")).split():
                thread = self._threads_by_id.get(cid)
                if thread is not None:
                    comment_selector = self.store.suggested_selector(thread)
                    break
        return {
            "nearest_id": nearest_id,
            "class_chain": " ".join(class_chain),
            "suggested_selector": comment_selector,
        }

    def _line_for(self, element: Any) -> int | None:
        line = getattr(element, "sourceline", None)
        if line:
            return int(line)
        markers = []
        if getattr(element, "attrs", None):
            if element.get("id"):
                markers.append(f'id="{element.get("id")}"')
            if element.get("data-hyp-cid"):
                markers.append(f'data-hyp-cid="{element.get("data-hyp-cid")}"')
        text = element.get_text(" ", strip=True) if hasattr(element, "get_text") else ""
        if text:
            markers.append(text[:80])
        for marker in markers:
            found = self.source.find(marker)
            if found != -1:
                return self.source.count("\n", 0, found) + 1
        return None


def render_human(payload: dict[str, Any], include_line_numbers: bool = False) -> str:
    kind = payload.get("kind")
    if kind in {"comments", "comment"}:
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if kind == "corpus":
        return payload["text"] or "corpus: empty"
    if kind == "doc":
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if kind == "element-set":
        return "\n\n".join(
            render_human(context, include_line_numbers) for context in payload["contexts"]
        )
    if kind in {"element", "selector"}:
        label = payload.get("comment_id") or payload.get("selector")
        if payload.get("relation"):
            label = f"{label} [{payload['relation']}]"
        lines = [f"{kind}: {payload.get('status')} {label}".rstrip()]
        if payload.get("anomaly"):
            lines.append(f"anomaly: {payload['anomaly']}")
        if not payload.get("matches"):
            lines.append("matches: 0")
            return "\n".join(lines)
        for index, match in enumerate(payload["matches"], start=1):
            suffix = f" line {match['line']}" if include_line_numbers and match.get("line") else ""
            lines.append(f"match {index}: <{match['tag']}>{suffix}")
            lines.append(match["html"])
        return "\n".join(lines)
    if kind == "search":
        lines = [
            f"search: {payload['count']} hit(s) for {payload['query']!r} "
            f"case-sensitive={str(payload['case_sensitive']).lower()}"
        ]
        if not payload["hits"]:
            lines.append("hits: 0")
            return "\n".join(lines)
        for index, hit in enumerate(payload["hits"], start=1):
            location = hit["location"]
            parts = [f"hit {index}"]
            if hit.get("line"):
                parts.append(f"line {hit['line']}")
            if location.get("nearest_id"):
                parts.append(f"id #{location['nearest_id']}")
            if location.get("class_chain"):
                parts.append(location["class_chain"])
            if location.get("suggested_selector"):
                parts.append(f"selector {location['suggested_selector']}")
            lines.append(" | ".join(parts))
            lines.append(hit["snippet"])
        return "\n".join(lines)
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _thread_matches(thread: dict[str, Any], state: str, agent: str) -> bool:
    if state == "open" and thread.get("resolved"):
        return False
    if state == "resolved" and not thread.get("resolved"):
        return False
    has_agent = bool(thread.get("agentInstruction"))
    if agent == "with" and not has_agent:
        return False
    if agent == "without" and has_agent:
        return False
    return True


def _css_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _attr_value(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _snippet(text: str, index: int, length: int, radius: int = 40) -> str:
    start = max(0, index - radius)
    end = min(len(text), index + length + radius)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix
