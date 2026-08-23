"""Claiming and releasing one key or one fenced block inside a config file
shared with the whole installed set.
"""
from __future__ import annotations

import json

from .constants import FENCE_ID


def _claim_id(rel: str, key: list[str] | None) -> str:
    return f"{rel}::" + (json.dumps(key) if key else "#block")


def _jget(doc: dict, key: list[str]):
    node = doc
    for k in key:
        if not isinstance(node, dict) or k not in node:
            return None, False
        node = node[k]
    return node, True


def _jset(doc: dict, key: list[str], value) -> None:
    node = doc
    for k in key[:-1]:
        node = node.setdefault(k, {})
    node[key[-1]] = value


def _jdel(doc: dict, key: list[str]) -> None:
    """Delete a key path and every container it leaves empty."""
    node = doc
    chain = [doc]
    for k in key[:-1]:
        if not isinstance(node, dict) or k not in node:
            return
        node = node[k]
        chain.append(node)
    if isinstance(node, dict):
        node.pop(key[-1], None)
    for i in range(len(chain) - 1, 0, -1):
        if isinstance(chain[i], dict) and not chain[i]:
            chain[i - 1].pop(key[i - 1], None)


def _fence(comment: str) -> tuple[str, str]:
    if comment == "#":
        return f"# {FENCE_ID}:start", f"# {FENCE_ID}:end"
    return f"<!-- {FENCE_ID}:start -->", f"<!-- {FENCE_ID}:end -->"


def _block_set(text: str, body: str, comment: str) -> str:
    start, end = _fence(comment)
    block = f"{start}\n{body.rstrip()}\n{end}\n"
    if start in text and end in text:
        head = text.split(start, 1)[0]
        tail = text.split(end, 1)[1].lstrip("\n")
        return head + block + tail
    return (text.rstrip() + "\n\n" if text.strip() else "") + block


def _block_del(text: str, comment: str) -> str:
    start, end = _fence(comment)
    if start not in text or end not in text:
        return text
    head = text.split(start, 1)[0]
    tail = text.split(end, 1)[1].lstrip("\n")
    return (head.rstrip() + "\n" + tail) if head.strip() else tail
