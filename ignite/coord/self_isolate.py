"""self_isolate — solo-run twin of the probe runner's tmux isolation (deploy/probe-suite.js).

The runner strips $TMUX and pins TMUX_TMPDIR for every child it spawns, so a probe/selftest run
THROUGH the suite is safe. One run BY HAND from inside a pane (G-163 forbids it — this is
defense-in-depth, not a licence) inherits neither, so a bare `tmux kill-server` reaches the
operator DEFAULT server and kills every session on the box. Call self_isolate_tmux() FIRST, before
any tmux touch and before importing any module that shells tmux: with $TMUX set it clears
$TMUX/$TMUX_PANE and pins TMUX_TMPDIR to a throwaway /tmp dir, so every later tmux command lands on
a socket no real session uses. No-op when $TMUX is unset — the suite child (runner already stripped
it) and any non-tmux caller pass through, so the runner stays PRIMARY and a second call cannot
double-isolate (the first pops $TMUX). Scratch rooted at the system tmp, never a long path — a
UNIX sun_path caps at ~108 bytes.
"""
import atexit
import os
import shutil
import tempfile


def self_isolate_tmux() -> str | None:
    if not os.environ.get("TMUX"):
        return os.environ.get("TMUX_TMPDIR")
    scratch = tempfile.mkdtemp(prefix="rbtv-tmux-")
    atexit.register(shutil.rmtree, scratch, ignore_errors=True)
    os.environ["TMUX_TMPDIR"] = scratch
    os.environ.pop("TMUX", None)
    os.environ.pop("TMUX_PANE", None)
    return scratch


if __name__ == "__main__":
    # ponytail self-check: `python3 self_isolate.py` — asserts the gate both ways.
    os.environ.pop("TMUX", None)
    assert self_isolate_tmux() == os.environ.get("TMUX_TMPDIR"), "no-op when $TMUX unset"
    os.environ["TMUX"] = "/tmp/fake,1,0"
    s = self_isolate_tmux()
    assert s and "rbtv-tmux-" in s, "pins a private scratch when $TMUX set"
    assert "TMUX" not in os.environ, "$TMUX cleared"
    assert "TMUX_PANE" not in os.environ, "$TMUX_PANE cleared"
    assert os.environ["TMUX_TMPDIR"] == s, "TMUX_TMPDIR pinned to scratch"
    assert self_isolate_tmux() == s, "idempotent second call ($TMUX already gone)"
    print("self_isolate self-check ok:", s)
