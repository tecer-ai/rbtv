"""The kit's ONE answer to "is this sitting alive?" — the supervisor registry, and nothing else.

⚠ THIS FILE EXISTS TO REPLACE THREE PREDICATES, NOT TO BECOME A FOURTH. Until spec-supervisor
§6 the kit answered liveness three disjoint ways and they could disagree:

  * a tmux pane (`tmux.py#live_panes`, `messages.py`'s `DEAD?` column) — a pane is a VIEWPORT.
    Closing one kills nothing and opening one proves nothing; a pane outlives its harness and a
    paneless daemon seat never had one.
  * the cgroup carrier (`carrier.py#carrier_self_session`) — that is IDENTITY [T2-R8], the answer
    to "who am I", and identity minting stays. It was never a heartbeat.
  * tick silence (`ticker.js`'s stall knobs) — a statement about WORK PRODUCT, whose home is
    spec-recovery's `last_progress_at`, not a process probe.

The registry answers instead: `kill(pid, 0)` plus the `/proc/<pid>/stat` field-22 start-time, on
the row the spawn door persisted. [T4-R8, C-15]

THE ANSWER IS THREE-VALUED AND THE THIRD VALUE IS THE POINT. `None` means the sitting has NO
registry row — born outside the daemon and not yet checked in, or predating the registry. It is
NOT "probably running" (that is the pane's answer) and NOT "dead": treating absence as death is
the mass-restamp hole C-15 names. Every caller here must branch on all three.

Stdlib only, one JSON document on stdout, same shape and same reasons as `ending_store.py` and
`supervisor_door.py` beside it.
"""
import json
import os
import subprocess
from pathlib import Path

PROBE_JS = Path(__file__).resolve().parent.parent / "supervisor" / "probe.js"


class LivenessError(Exception):
    pass


def _probe(argv):
    cmd = ["node", str(PROBE_JS)] + argv
    reg = os.environ.get("SUPERVISOR_REGISTRY")
    if reg:
        cmd += ["--registry", str(reg)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise LivenessError((proc.stderr or proc.stdout or "liveness probe failed").strip())
    text = (proc.stdout or "").strip()
    return json.loads(text) if text else {}


def goal_of(pkg):
    """The goal name a package path carries — the key half every registry row is written under."""
    return Path(pkg).name if pkg else ""


def sitting_alive(pkg, seat):
    """True / False / None for one sitting. None is UNSUPERVISED — never assume either way.

    Never raises at the call site: a probe that cannot run answers None, which routes the caller
    down the same "we do not know" arm an unregistered sitting takes. A liveness question that
    throws would turn an unreachable node binary into a mass verdict, which is the shape of the
    incident this whole surface exists to close."""
    try:
        return _probe(["--goal", goal_of(pkg), "--seat", str(seat)]).get("alive")
    except (LivenessError, ValueError, OSError):
        return None


def goal_liveness(pkg):
    """{seat: {supervised, alive, pid, launch_token}} for a whole goal, in ONE call.

    Rendering a roster asks this question once per seat, and N subprocess round trips per render
    is exactly the cost that made the pane predicate attractive in the first place."""
    try:
        answer = _probe(["--goal", goal_of(pkg)])
    except (LivenessError, ValueError, OSError):
        return {}
    return answer if isinstance(answer, dict) else {}


def goal_liveness_strict(pkg):
    """Same one-call answer as `goal_liveness`, but RAISES instead of swallowing.

    `goal_liveness` reads `{}` on both "this goal has no live sittings" (a normal, common state —
    nothing has launched yet, or everything has ended) and "the probe itself could not run" (node
    missing, a corrupt registry file). A consumer that must tell those apart — a capacity gate
    deciding whether to trust a zero — cannot use the swallowing form: both answers are the same
    empty dict. This raises `LivenessError` on the second case so the caller's own D1-shaped
    branch (census could not be produced) fires on an actual sensor fault, never on an empty room.
    """
    answer = _probe(["--goal", goal_of(pkg)])
    return answer if isinstance(answer, dict) else {}


def liveness_word(alive):
    """The ONE rendering of the three-valued answer, so seven consumers cannot spell it eight ways.

    `unsupervised` is deliberately not a scare word: a console-uncaged seat that has not checked in
    yet is a normal state, not a defect [T4-R8]."""
    if alive is True:
        return "alive"
    if alive is False:
        return "dead"
    return "unsupervised"


def occupied(pkg, seat, pane_hint=False):
    """Is a PRIOR sitting of `seat` still running? The double-launch walls' one predicate.

    Every wall that used to read `prior["pane"] in live_panes()` asks THIS instead. The three-valued
    answer is collapsed here, once, and it fails CLOSED on the unknown arm:

      alive is True   -> occupied. The registry says the process is there.
      alive is False  -> free. The registry says it is gone, and a pane that outlived it is a
                         viewport, not a reason to refuse a launch [T4-R8].
      alive is None   -> UNSUPERVISED, so the registry has nothing to say. Only here does the pane
                         hint decide, and it decides toward refusal — a wall whose job is to stop
                         two live sessions under one name must not open on ignorance.

    Collapsing it anywhere else is how three predicates became three answers."""
    alive = sitting_alive(pkg, seat)
    if alive is None:
        return bool(pane_hint)
    return alive


__all__ = ["LivenessError", "goal_of", "sitting_alive", "goal_liveness", "goal_liveness_strict",
           "liveness_word", "occupied", "PROBE_JS"]
