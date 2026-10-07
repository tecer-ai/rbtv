"""Rewriting, in a copy the program writes away from its source's folder, the
target of a markdown link into the absolute path of that file on this machine:
a link the author wrote from the repository root or from `.rbtv/`, and, in the
copy of a skill or a command, a link written from the source's own folder.
"""
from __future__ import annotations

import re
from pathlib import Path

from discovery import module_folders

from .constants import REPO_ROOT

# A fenced code block, or an inline code span: a link written there is an
# example the reader copies, so it is left as written.
_CODE = re.compile(r"^(?P<fence>`{3,}|~{3,}).*?^(?P=fence)[^\n]*$"
                   r"|(?P<tick>`+)(?:(?!\n\n).)+?(?P=tick)", re.S | re.M)
# `[text](target)` and `[text](target "title")`; the target may be `<in angles>`.
_LINK = re.compile(r"(\[[^\]\n]*\]\()(<[^>\n]*>|[^)\s]+)([^)\n]*\))")
INSTALLATION_PREFIX = ".rbtv/"
# `scheme:…` (a URL, `mailto:`, a Windows drive) or a path from the root.
_URL_OR_ABSOLUTE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:|[/\\]")


def absolute_links(text: str, installation: Path | None,
                   repo_root: Path = REPO_ROOT, base: Path | None = None) -> str:
    """`text` with each markdown link target that starts with `.rbtv/` joined
    to `installation`, and each that starts with the name of a module of the
    repository joined to `repo_root`. A URL, an anchor and an absolute path are
    left as written, and so is a `.rbtv/` target when there is no installation.
    Any other path is relative to the folder of the source: it is joined to
    `base` when the copy leaves that folder, and left as written without one."""
    modules = set(module_folders(repo_root))

    def absolute(match: re.Match) -> str:
        target = match.group(2)
        angled = target.startswith("<")
        path, mark, fragment = target.strip("<>").partition("#")
        if path.startswith(INSTALLATION_PREFIX):
            root = installation
        elif "/" in path and path.split("/", 1)[0] in modules:
            root = repo_root
        elif path and not _URL_OR_ABSOLUTE.match(path):
            root = base
        else:
            root = None
        if root is None:
            return match.group(0)
        written = (root / path).resolve().as_posix() + mark + fragment
        if angled or re.search(r"[\s()]", written):
            written = f"<{written}>"
        return match.group(1) + written + match.group(3)

    out, at = [], 0
    for code in _CODE.finditer(text):
        out += [_LINK.sub(absolute, text[at:code.start()]), code.group(0)]
        at = code.end()
    out.append(_LINK.sub(absolute, text[at:]))
    return "".join(out)
