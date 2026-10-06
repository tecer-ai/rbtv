"""Rewriting, in a copy the program writes away from its source's folder, the
target of a markdown link that the author wrote from the repository root or
from `.rbtv/` into the absolute path of that file on this machine.
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


def absolute_links(text: str, installation: Path | None,
                   repo_root: Path = REPO_ROOT) -> str:
    """`text` with each markdown link target that starts with `.rbtv/` joined
    to `installation`, and each that starts with the name of a module of the
    repository joined to `repo_root`. A URL, an anchor and a relative path are
    left as written, and so is a `.rbtv/` target when there is no installation."""
    modules = set(module_folders(repo_root))

    def absolute(match: re.Match) -> str:
        target = match.group(2)
        angled = target.startswith("<")
        path, mark, fragment = target.strip("<>").partition("#")
        if path.startswith(INSTALLATION_PREFIX) and installation is not None:
            root = installation
        elif "/" in path and path.split("/", 1)[0] in modules:
            root = repo_root
        else:
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
