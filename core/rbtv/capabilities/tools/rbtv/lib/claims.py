"""Claiming and releasing one key or one fenced block inside a config file
shared with the whole installed set.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from discovery import Refuse

from .constants import FENCE_ID, GUIDANCE_FILE, LEGACY_FENCE_ID


# The end line of a block this installer wrote, now or under the 0.2 fence.
_OWN_END = re.compile(r"<!-- rbtv2?:end[^>]*-->\Z")
_OWNED_LABELS = re.compile(r"<!-- rbtv2?:start (.+?) -->")


def _claim_id(rel: str, key: list[str] | None, label: str | None = None) -> str:
    """One claim: a JSON key path, or a fenced block. A block carries its label
    when the file holds several (a component's section of folder instructions)."""
    if key:
        return f"{rel}::" + json.dumps(key)
    return f"{rel}::#block" + (f":{label}" if label else "")


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


def _fence(comment: str, label: str | None = None,
           fence_id: str = FENCE_ID) -> tuple[str, str]:
    """The start and end lines of one fenced block. `label` names one of
    several blocks in a file; none names the file's single unlabeled block."""
    suffix = f" {label}" if label else ""
    if comment == "#":
        return f"# {fence_id}:start{suffix}", f"# {fence_id}:end{suffix}"
    return f"<!-- {fence_id}:start{suffix} -->", f"<!-- {fence_id}:end{suffix} -->"


def _located(text: str, comment: str, label: str | None
             ) -> tuple[str, str] | None:
    """The fence pair this block is written under in *text*: the current one,
    else the one the 0.2 installer wrote. None when the block is absent."""
    for fence_id in (FENCE_ID, LEGACY_FENCE_ID):
        start, end = _fence(comment, label, fence_id)
        if comment == "#":
            # `# rbtv:start` is a prefix of `# rbtv:start <label>`: a `#` fence
            # matches only as a whole line, so the returned markers carry
            # their line end (none for an end marker closing the file).
            start += "\n"
            if end + "\n" in text:
                end += "\n"
            elif not text.endswith(end):
                continue
        if start in text and end in text:
            return start, end
    return None


def _instruction_block_valid(text: str, rel: str, path: Path) -> bool:
    """A root instruction file has zero or one complete owned section (the
    unlabeled one; component sections carry a label and are checked apart)."""
    pairs = [_fence("<!--", None, fid) for fid in (FENCE_ID, LEGACY_FENCE_ID)]
    starts = sum(text.count(start) for start, _ in pairs)
    ends = sum(text.count(end) for _, end in pairs)
    if not (starts or ends):
        return False
    start, end = next(((s, e) for s, e in pairs if s in text or e in text))
    if (starts != 1 or ends != 1 or text.count(start) != 1
            or text.count(end) != 1 or text.index(start) > text.index(end)):
        raise Refuse(
            "guidance-section-malformed",
            f"{rel} has an incomplete, duplicate, or reversed rbtv "
            "instruction section; inspect its fences before retrying. "
            "Nothing was written",
            str(path))
    return True


def owned_fence_claims(target: Path, planned: set[str], state: dict,
                       harnesses: list[str]) -> set[str]:
    """Stale labelled fences in shared destinations this target can own.

    A fence alone does not establish ownership: ordinary documents can quote
    one.  The plan and book identify destinations this installation has used;
    `GUIDANCE_FILE` supplies each receiving harness's fixed root destination,
    so a lost book can still release a stale root instruction section.
    """
    paths = {cid.partition("::")[0] for cid in planned}
    paths.update(state.get("shared_files") or [])
    paths.update(cid.partition("::")[0]
                 for cid in state.get("shared_claims") or [])
    paths.update(GUIDANCE_FILE[harness] for harness in harnesses
                 if harness in GUIDANCE_FILE)
    found: set[str] = set()
    for rel in paths:
        path = target / rel
        if path.suffix != ".md" or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label in _OWNED_LABELS.findall(text):
            cid = _claim_id(rel, None, label)
            if cid not in planned and _located(text, "<!--", label):
                found.add(cid)
    return found


def _block_set(text: str, body: str, comment: str,
               *, preserve_outside: bool = False,
               label: str | None = None, first: bool = False) -> str:
    start, end = _fence(comment, label)
    block = f"{start}\n{body.rstrip()}\n{end}\n"
    found = _located(text, comment, label)
    if found:
        head = text.split(found[0], 1)[0]
        tail = text.split(found[1], 1)[1]
        if preserve_outside:
            return head + block.rstrip("\n") + tail
        # `block` ends its own line; drop only the newline that ended the old
        # end marker (unless the marker found already carried it), so the
        # blank line before a following block survives.
        if not found[1].endswith("\n") and tail.startswith("\n"):
            tail = tail[1:]
        return head + block + tail
    if first:
        # A new block that must precede everything else (a TOML root key
        # cannot follow a table header).
        return block + ("\n" + text if text.strip() else "")
    if preserve_outside:
        gap = "" if not text or text.endswith("\n") else "\n"
        return text + gap + block.rstrip("\n")
    return (text.rstrip() + "\n\n" if text.strip() else "") + block


def _block_del(text: str, comment: str,
               *, preserve_outside: bool = False,
               label: str | None = None) -> str:
    found = _located(text, comment, label)
    if not found:
        return text
    head = text.split(found[0], 1)[0]
    tail = text.split(found[1], 1)[1]
    if preserve_outside:
        # The newline `_block_set` put between two of our blocks goes with the
        # block it separated; the owner's own newlines never do.
        if not tail and head.endswith("\n") and _OWN_END.search(head[:-1]):
            head = head[:-1]
        elif tail.startswith("\n<!-- " + FENCE_ID):
            tail = tail[1:]
        return head + tail
    tail = tail.lstrip("\n")
    return (head.rstrip() + "\n" + tail) if head.strip() else tail
