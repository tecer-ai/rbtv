import os
import re
import shlex
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

def is_tmux_pane(s):
    """True only for a real tmux pane id (`%N`) — the one token tmux may be handed as `-t`."""
    return bool(s) and s.startswith("%")


def detect_pane(override=None):
    if override:
        return override
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return ""
    r = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane, "#{pane_id}"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else pane


# ---------- injection write-log (task 7.39; owner ruling `r-739-payload-text`) ----------------
#
# Every agent-to-agent keystroke injection writes ONE attributed line: WHO injected, into WHICH
# seat/pane, WHEN, WHICH action, and THE FULL PAYLOAD TEXT. The payload is recorded on the owner's
# explicit ruling (2026-07-27), taken AGAINST the metadata-only recommendation with the exposure on
# the table: it re-creates the R1-dropped keystroke-transcript class for agent-to-agent injections
# only. That call is the owner's, not this code's — do not re-decide it here.
#
# The log is NEVER-COMMIT / NEVER-PUSH: same exposure class as raw scrollback (issues G-3). It is
# written into the run package's `coordination/` dir, which lives under `.rbtv/goals/**` and is
# untracked, and it is chmod 0600 (task 7.13 tightened this artifact class 664 -> 0600).
#
# TWO PROPERTIES THAT ARE DELIBERATE, both from task 7.13's retention ruling:
#   FAILS OPEN, ALWAYS — a logging error NEVER blocks or fails an injection. 7.13 ruled that a
#   fail-closed audit disables the very function it audits. Here it would be worse: all keystroke
#   injection funnels through these three primitives, so an unwritable path would silence EVERY
#   seat at once. Every entry point below swallows its own exceptions and returns False.
#   AGE SWEEP, NEVER A SIZE CAP — 7.13 criterion (2) rejects size caps in those words, because a
#   cap either fires fail-closed or silently discards evidence. Window is env-configurable,
#   default 90 days, 0 = never delete, values below 7 refused (a typo must not erase the trail).

INJECTION_LOG = "injections.log"
INJECTION_RETENTION_DAYS = 90          # 7.13 default
INJECTION_RETENTION_MIN = 7            # 7.13: below this is REFUSED, never honoured
INJECTION_RETENTION_ENV = "COORD_INJECTION_RETENTION_DAYS"

# who/action/base for the primitives, which are module-level and receive no `args`.
_INJECTION = {"agent": "", "action": "", "base": None}
_INJECTION_PRUNED = False
_INJECTION_SWEEP_LOCK = threading.Lock()


def set_injection_context(agent=None, action=None, base=None):
    """Tell the injection log who is calling, why, and where the package is (7.39).

    The three tmux primitives take only `(pane, text)`, so identity, action and package land here
    instead of being threaded through every call site. Anything left unset falls back at write
    time to $COORD_AGENT / $COORD_PACKAGE / the calling pane's roster row — which is what covers
    watch.py's internal API path, since it runs outside any pane."""
    if agent is not None:
        _INJECTION["agent"] = (agent or "").strip()
    if action is not None:
        _INJECTION["action"] = (action or "").strip()
    if base is not None:
        _INJECTION["base"] = Path(base)


def injection_retention_days():
    """7.13's window. Default 90; 0 = never delete; below INJECTION_RETENTION_MIN is REFUSED and
    falls back to the default, because a mistyped '1' must not silently erase the audit trail.
    An unparseable value is treated the same way — fail open, keep evidence."""
    raw = os.environ.get(INJECTION_RETENTION_ENV, "").strip()
    if not raw:
        return INJECTION_RETENTION_DAYS
    try:
        days = int(raw)
    except ValueError:
        return INJECTION_RETENTION_DAYS
    if days == 0:
        return 0
    if days < INJECTION_RETENTION_MIN:
        return INJECTION_RETENTION_DAYS
    return days


def injection_log_path():
    """The log's home: `{package}/coordination/injections.log`. None when no package resolves —
    in which case nothing is logged and nothing fails."""
    base = _INJECTION.get("base")
    if base is None:
        pkg = os.environ.get("COORD_PACKAGE", "").strip()
        if not pkg:
            return None
        base = Path(pkg) / "coordination"
    return Path(base) / INJECTION_LOG


def injection_payload_repr(payload):
    """One line, full text, reversible. The payload is recorded VERBATIM per the owner's ruling —
    never truncated, never hashed — but the log stays line-oriented (one line per injection, so it
    greps and tails), so the four characters that would break that are escaped."""
    if payload is None:
        return "(none)"
    return (str(payload).replace("\\", "\\\\").replace("\t", "\\t")
            .replace("\r", "\\r").replace("\n", "\\n"))


def prune_injection_log(path, days):
    """7.13 AGE sweep. Drops entries older than the window; NEVER caps by size. A line whose
    timestamp will not parse is KEPT — evidence we cannot date is still evidence.

    CHEAP-CHECKS FIRST, AND THAT IS A CORRECTNESS PROPERTY, NOT AN OPTIMISATION. A sweep is a
    read-then-rewrite, and `deliver_wakes` fans out to recipients CONCURRENTLY (ThreadPoolExecutor),
    so a rewrite racing an append from another thread or another `coordinate` process would silently
    LOSE that line — in the one file whose whole purpose is that nothing is lost. Since entries are
    appended in time order, the OLDEST line is the first one: if it is inside the window there is
    nothing to drop, so we return having only read one line and never open the file for writing.
    With a 90-day window that makes the racy path run about once per 90 days instead of once per
    process. The rewrite itself then takes the package lock, and the caller holds a thread lock."""
    if days <= 0 or not path.exists():
        return
    cutoff = datetime.now() - timedelta(days=days)
    try:  # one line, not the file: is there anything old enough to be worth a rewrite?
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
        if not first.strip():
            return
        if datetime.fromisoformat(first.split("\t", 1)[0]) >= cutoff:
            return  # oldest entry is inside the window -> nothing to sweep, no rewrite
    except (ValueError, IndexError, OSError):
        pass  # undateable or unreadable first line -> fall through to the full pass
    kept, dropped = [], 0
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            if datetime.fromisoformat(ln.split("\t", 1)[0]) < cutoff:
                dropped += 1
                continue
        except (ValueError, IndexError):
            pass
        kept.append(ln)
    if dropped:
        # Under the package lock: `coordinate` processes serialize their read-modify-writes here,
        # which is the same guard the roster and message-id allocation use.
        with coord_lock(path.parent):  # the log lives IN the coordination dir the lock guards
            path.write_text("".join(f"{ln}\n" for ln in kept), encoding="utf-8")


def log_injection(pane, primitive, payload):
    """Append ONE attributed line for one keystroke injection (7.39). Returns True when written.

    NEVER RAISES. Every failure path returns False and the injection proceeds — see this section's
    header for why fail-open is a requirement here and not a convenience."""
    global _INJECTION_PRUNED
    try:
        path = injection_log_path()
        if path is None:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        # Wakes fan out concurrently, so the once-per-process sweep takes a thread lock: two
        # threads must never rewrite this file at the same time. The append below needs no lock —
        # one short line opened "a" is atomic under POSIX O_APPEND, across threads and processes.
        with _INJECTION_SWEEP_LOCK:
            if not _INJECTION_PRUNED:
                _INJECTION_PRUNED = True
                try:
                    prune_injection_log(path, injection_retention_days())
                except Exception:
                    pass
        who = _INJECTION.get("agent") or os.environ.get("COORD_AGENT", "").strip()
        if not who:
            try:
                who = pane_agent(path.parent, detect_pane()) or ""
            except Exception:
                who = ""
        seat = ""
        try:
            seat = pane_agent(path.parent, pane) if pane else ""
        except Exception:
            seat = ""
        # Every injection entry point names its OWN action, so a later call can never inherit an
        # earlier one's label — the first draft of this logged a `/rename` as `approve:rename`
        # because it reused whatever `cmd_approve` had set. An unnamed action logs the bare
        # primitive, which is honest; a WRONG one is worse than none in a forensic log.
        ctx = _INJECTION.get("action", "")
        if ctx == primitive:
            ctx = ""
        line = "\t".join((
            datetime.now().isoformat(timespec="seconds"),
            who or "(unresolved)",
            seat or "(unregistered)",
            pane or "(no-pane)",
            f"{ctx}:{primitive}" if ctx else primitive,
            injection_payload_repr(payload),
        ))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return True
    except Exception:
        return False


# ---------- tmux wrappers (every tmux touch goes through one of these, so selftest can stub) ----

def set_pane_title(pane, title):
    """Name the tmux pane after the agent (visible via pane-border-status)."""
    if not is_tmux_pane(pane):
        return   # F1: a session-id token is not a tmux target
    subprocess.run(["tmux", "select-pane", "-t", pane, "-T", title],
                   capture_output=True, text=True)


RENAME_ACTION = "rename-scheduled"


def rename_injection_note(agent, delay, expected_title=None):
    """The write-log payload for a SCHEDULED rename (G-53). Pure, so it is testable without the
    detached subshell — and the reason it exists is that the shell is exactly what makes the
    delivery unobservable."""
    return (f"/rename {agent} (scheduled: detached, fires in ~{delay}s via raw tmux ONLY IF the "
            f"pane title still reads '{expected_title or agent}'; "
            f"delivery is NOT observed by this log)")


def rename_injection_script(pane, agent, delay, expected_title):
    """The detached subshell's bash, pure so the selftest can prove the guard both ways.

    FIRE-TIME GUARD (owner-session rename incident, 2026-08-10): the /rename keystrokes go out
    ONLY if, at fire time, the pane still exists AND its pane title still reads the title set at
    boot (`set_pane_title` precedes every scheduling call site). A dead pane, a reused pane id
    (`%N` is per-server and restarts with the server, so after a tmux server restart — or against
    a different socket — the same id names a stranger's pane), or any foreign pane fails the
    title read and the script exits 0 without typing. Measured before the guard: three of the
    owner's own interactive sessions renamed to `elicitator` by this script firing at pane ids
    the seat no longer owned."""
    return (f"sleep {delay}; "
            f"t=$(tmux display-message -p -t {shlex.quote(pane)} '#{{pane_title}}' 2>/dev/null)"
            f" || exit 0; "
            f"[ \"$t\" = {shlex.quote(expected_title)} ] || exit 0; "
            f"tmux send-keys -t {shlex.quote(pane)} -l {shlex.quote('/rename ' + agent)}; "
            f"sleep 1; tmux send-keys -t {shlex.quote(pane)} Enter")


def schedule_session_rename(pane, agent, delay=25, expected_title=None):
    """Inject `/rename <agent>` into the pane's Claude session once it has had time to boot.

    Detached (coord.py returns immediately); failures are silent — the rename is cosmetic and a
    lost keystroke must never block a launch. claude harness only: codex/opencode have no
    /rename — their seats are identified by pane/window title alone.

    `expected_title` is the pane title the fire-time guard demands (see
    `rename_injection_script`); it defaults to the agent name, which is what every launch-path
    caller sets — the closer path sets `closer-<target>` and passes it explicitly."""
    # G-53: this logs INTENT, not injection. The keystrokes are sent by the DETACHED subshell
    # below, ~25s later, with raw `tmux send-keys` that never touches the instrumented primitives
    # — so nothing here can know whether they landed, and the line would read identically if the
    # pane had died in the meantime. writelog proved it by observation: zero entries across every
    # pane in the window where the real keystrokes went out. The action name now says what the
    # line actually attests, so the write-log stops asserting what it cannot know.
    set_injection_context(action=RENAME_ACTION)  # our own action: never inherit a caller's
    log_injection(pane, RENAME_ACTION, rename_injection_note(agent, delay, expected_title))
    script = rename_injection_script(pane, agent, delay, expected_title or agent)
    subprocess.Popen(["bash", "-c", script], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def live_panes():
    """Set of pane ids tmux currently knows. Empty set when tmux is unavailable.

    ⚠ THIS IS NOT A LIVENESS PREDICATE AND NO CALLER MAY USE IT AS ONE [T4-R8, C-15]. It answers
    ONE mechanical question — can a wake reach this pane through tmux right now — and a pane is a
    VIEWPORT: it outlives the harness that ran in it, a daemon-lane seat never had one, and closing
    one kills nothing. "Is this sitting alive?" is `liveness.sitting_alive` / `liveness.occupied`,
    which probe the supervisor registry (pid + /proc start-time) and nothing else. spec-supervisor
    §6 retired this predicate as liveness; what survives is the viewport enumeration below."""
    r = subprocess.run(["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return set()
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


# P38/8(b) — a seat parked on its harness's interactive approval prompt is a BLIND GATE: the pane
# is frozen on a modal, so a wake typed into it is not read, and worst case lands as stray text
# inside the modal's own input. codex advertises the state in the pane TITLE ("Action Required").
# The title is the only signal used on purpose: matching the pane's visible TEXT would false-fire
# on any seat whose output happens to contain the phrase (a briefing quoting it, a log line).
# codex is the only rostered harness that publishes such a title today — extending this to another
# harness needs a real captured pane in the gated state, the same discipline P35 round 2 imposed.
APPROVAL_TITLE_MARKERS = ("action required",)


def pane_title(pane):
    """Current tmux title of a pane. '' when tmux is unavailable or the pane is gone."""
    if not is_tmux_pane(pane):
        return ""   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "-F", "#{pane_title}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def at_approval_gate(pane):
    """True when this pane's TITLE says its harness is parked on an interactive approval prompt.

    Fail-safe by construction: an unreadable title, a dead pane, or no tmux all return '' and
    therefore False — a seat is never treated as gated on the strength of a missing signal."""
    if not pane:
        return False
    title = pane_title(pane).lower()
    return any(m in title for m in APPROVAL_TITLE_MARKERS)


WAKE_ENTER_ATTEMPTS = 3
# A real production wake (300+ chars) takes some TUIs noticeably longer than round-2's 0.15s
# first-check assumed just to REDRAW the pasted text, before Enter's effect is even relevant — a
# check that fires before the redraw catches up cannot tell "still stranded" apart from "hasn't
# rendered yet" (both look like "text absent from composer"), so it silently skips verification
# on exactly the pane class it's slowest on. Round-3 live-stress finding: a real 323-char wake on
# a rostered-width (114-col) opencode pane took ~0.6-0.85s (3 trials, cold and warm) to redraw
# EITHER outcome (stranded-and-still-there, or typed-then-cleared) — the composer is frozen on
# its pre-send content for that whole window regardless of whether Enter lands. Claude Code
# resolves in <0.15s (round-2 evidence, reconfirmed). WAKE_ENTER_VERIFY_DELAY_FIRST is set with
# margin over the slower harness's observed worst case; this trades some latency on the fast
# common path (every send now pays it, not just genuine retries) for not being blind on the
# slower one — the same failure MODE the wrap fix above addresses, just a different cause.
WAKE_ENTER_VERIFY_DELAY_FIRST = 1.3
WAKE_ENTER_VERIFY_DELAY_RETRY = 0.6   # a retry's pane has already rendered the paste once by
                                       # here (live-verified: a genuine second Enter's effect
                                       # still resolves within this window — round-3 evidence)
WAKE_TAIL_LINES = 20  # on-screen lines scanned for the still-unsubmitted composer line
# A production wake line (310-319 chars) hard-wraps in EVERY rostered pane (narrowest 114 cols) —
# `capture-pane -J` cannot rejoin a TUI's own wrap points (verifier-tick round-2, msg #188). Only
# a PREFIX of the wake text is guaranteed to render intact on the composer's first on-screen line;
# 60 chars covers '[coord wake] New coordination message #N from <sender> ' (unique per send) with
# wide margin under the narrowest rostered composer width.
WAKE_PREFIX_LEN = 60

# Claude Code draws its composer as one or more lines sandwiched between two horizontal rule
# lines (the top rule may carry the pane's tmux title, e.g. '───── toolsmith-2 ──'); a wake line
# wider than the pane hard-wraps across several composer lines. Status/hint chrome always renders
# BELOW the bottom rule, never between the rules. Requiring the sandwich — not just the '❯' glyph
# alone — also guards against a false match on a shell PS1 prompt that reuses the same glyph
# (starship-themed shells) sitting anywhere in cooked-mode scrollback.
_RULE_RUN = "─" * 10  # '──────────'

# P35-ghost (G-master-0804-2200, root-caused 2026-08-04): Claude Code renders a SUGGESTED next
# prompt inside the composer sandwich as FAINT text (SGR 2 — `ESC[2m…ESC[0m`), regenerated from
# the session's own context after a turn ends. It LOOKS like a stranded draft in a plain capture
# and reads like a seat's note-to-self ('check execution-tactical-designer checkout' recurring in
# the chief-of-staff pane), but it is UI chrome, not input: nothing ever typed it (no injection
# log, session file, or history entry holds it), Enter does not submit it, and real keystrokes
# replace it — nudges submitted CLEAN through it while two flush-Enters "failed" against it.
# Faint is the discriminator: typed input renders at normal intensity, the ghost never does. So
# composer-emptiness is judged on an ESCAPED capture with faint spans erased first — a plain
# capture is structurally blind to the one bit that separates a ghost from a draft.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_FAINT_RE = re.compile(r"\x1b\[2m.*?(?:\x1b\[(?:0|22)m|$)")


def _strip_ansi(line):
    return _ANSI_RE.sub("", line)

# opencode draws its composer inside a '┃'-bordered box: a blank pad line, the composer's own
# content line, another blank pad, then a 'Build · <model>' status line, in that order — the
# composer is the FIRST non-blank line in the box's bottom-most run, not the last (that's the
# model-status footer).
_OPENCODE_BORDER = "┃"


def tmux_send_text(pane, text):
    if not is_tmux_pane(pane):
        return False, "not a tmux pane"   # F1: a session-id token is not a tmux target
    log_injection(pane, "text", text)
    r = subprocess.run(["tmux", "send-keys", "-t", pane, "-l", text], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_send_enter(pane):
    if not is_tmux_pane(pane):
        return False, "not a tmux pane"   # F1: a session-id token is not a tmux target
    log_injection(pane, "enter", "<Enter>")
    r = subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_capture_tail(pane, lines=WAKE_TAIL_LINES, escapes=False):
    """Last N on-screen lines of a pane, soft-wraps rejoined (-J). Returns (text, err).
    `escapes` adds -e so SGR styling survives — the one bit that tells a P35-ghost from a draft."""
    if not is_tmux_pane(pane):
        return "", "not a tmux pane"   # F1: a session-id token is not a tmux target
    cmd = ["tmux", "capture-pane", "-p", "-J", "-t", pane, "-S", f"-{lines}"]
    if escapes:
        cmd.insert(2, "-e")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return "", r.stderr.strip()
    return r.stdout, ""


def _locate_claude_composer_idx(lines):
    """Index of the bottom-most rule-sandwiched composer's TOP line, or None. Scans from the
    screen bottom for a rule line (the sandwich's bottom rule), then walks upward collecting
    composer line(s) until the matching top rule. A sandwich with zero lines between the rules
    (top rule immediately above the bottom rule) is not a real composer and is skipped."""
    for i in range(len(lines) - 1, 1, -1):
        if not lines[i].startswith(_RULE_RUN):
            continue
        j = i - 1
        while j >= 0 and not lines[j].startswith(_RULE_RUN):
            j -= 1
        if j < 0 or j == i - 1:
            continue
        return j + 1
    return None


def _locate_claude_composer(lines):
    """The composer's TOP-most line text — the one a hard-wrapped wake's prefix starts on."""
    i = _locate_claude_composer_idx(lines)
    return None if i is None else lines[i]


def _locate_opencode_composer(lines):
    run_start = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].lstrip().startswith(_OPENCODE_BORDER):
            run_start = i
        elif run_start is not None:
            break
    if run_start is None:
        return None
    run_end = run_start
    while run_end < len(lines) and lines[run_end].lstrip().startswith(_OPENCODE_BORDER):
        run_end += 1
    for line in lines[run_start:run_end]:
        if line.lstrip().lstrip(_OPENCODE_BORDER).strip():
            return line
    return None


def _locate_composer_line(tail):
    """Return the pane's live composer text from an ESCAPED capture, or None when the capture
    matches no known composer structure (an unrecognized TUI, or a cooked-mode pane with no
    composer at all). Faint spans are erased and styling stripped BEFORE structure detection, so
    a P35-ghost never reads as composer content. Callers MUST treat None as fail-safe: do not
    retry, do not report failure."""
    lines = [_strip_ansi(_FAINT_RE.sub("", l)) for l in tail.splitlines()]
    return _locate_claude_composer(lines) or _locate_opencode_composer(lines)


def _wake_unsubmitted(pane, text):
    """True while `text` is still sitting in the pane's live composer — the Enter that should
    have submitted it was dropped by a busy/streaming pane (P35). False once the composer no
    longer holds it, OR when the pane's chrome does not match a known composer structure: an
    unparseable pane fails SAFE (today's single-Enter behavior — never retried, never reported
    as a delivery failure) rather than risking a false stranded-retry or a false failure on a
    pane this code cannot read (round-2 fix, verifier-tick #145 — the prior 'last non-blank
    line' check was blind on every rostered TUI, since each renders status/hint chrome below the
    composer). Matches only a bounded PREFIX of `text`, not the full line: a production wake
    (310-319 chars) hard-wraps across several composer lines in every rostered pane, and
    `capture-pane -J` cannot rejoin a TUI's own wrap points — the full text is never one
    contiguous captured line, but its first WAKE_PREFIX_LEN chars always render intact on the
    composer's top-most line (round-3 fix, verifier-tick round-2 re-verification). A capture
    error is likewise treated as submitted: send-keys already reported success and there is
    nothing further to act on."""
    tail, err = tmux_capture_tail(pane, escapes=True)
    if err:
        return False
    composer = _locate_composer_line(tail)
    if composer is None:
        return False
    return text[:WAKE_PREFIX_LEN] in composer


def composer_real_text(tail):
    """The composer's REAL (typed, non-ghost) visible text from an ESCAPED capture — None when
    no Claude composer is located, '' when the composer is empty or holds only a P35-ghost.
    Pure, so the selftest can drive it with captured pane bytes and no tmux. Faint (SGR 2)
    spans are erased FIRST — they are the harness's own suggestion chrome, never input — then
    all remaining styling is stripped and the prompt glyph discounted."""
    raw = tail.splitlines()
    idx = _locate_claude_composer_idx([_strip_ansi(l) for l in raw])
    if idx is None:
        return None
    text = _strip_ansi(_FAINT_RE.sub("", raw[idx])).strip()
    return "" if text == "❯" else text


def _composer_nonempty(pane):
    """True when the pane's Claude composer already holds real content BEFORE a wake types into
    it. Judged on the ESCAPED capture so the harness's faint ghost suggestion is not mistaken
    for a stranded draft (P35-ghost, G-master-0804-2200: two flush-Enters "failed" against ghost
    text nothing had typed, and every wake to the pane was refused — while real nudges submitted
    clean through the same composer). Only the Claude composer is judged: opencode's idle
    composer renders a placeholder ("Ask anything...") this check cannot tell from a draft, so
    opencode panes fail safe. Capture error / no composer located → False (fail-safe: proceed
    exactly as today)."""
    tail, err = tmux_capture_tail(pane, escapes=True)
    if err:
        return False
    return bool(composer_real_text(tail))


def wake(pane, text):
    """Type `text` into `pane` and submit it. A busy/streaming pane can eat the Enter keystroke
    without submitting (P35) even though text and Enter are already separate send-keys calls
    (§17.3) — verify the wake line actually left the composer and, if not, re-send ONLY Enter
    (never retype text), bounded to WAKE_ENTER_ATTEMPTS. Every send pays the first verify delay
    (see its constant for why a "short fixed delay, only retries pay more" split does not hold at
    real wake length); a retry (genuinely stranded after the first Enter) pays the shorter settle
    delay on top, since by then the pane has already rendered the paste once.

    REFUSES multi-line text (G-11). `tmux send-keys -l` delivers an embedded newline as Enter, so
    multi-line text is EXECUTED LINE BY LINE by whatever reads the pane. Reproduced 2026-07-27 in
    a throwaway pane: a closer's markdown prompt sent this way into a bash/ble.sh pane ran its
    `coordinate checkin` line for real and printed its completion line — a seat that reported done
    while no harness had ever started, and wake() returned SUCCESS. Any text long enough to be
    multi-line goes through a file (prompt_file) so the wake line stays one line.

    REFUSES a pane whose composer already holds content one flush Enter does not clear
    (P35-draft). Pre-existing composer content in the chief-of-staff pane silently ate 39 wakes
    over ~4h (2026-08-04): each wake stacked its text after that content, its Enter did not
    submit, and the prefix-verify — which reads only the TOP composer line, held by that content
    — reported success. WHAT PUT IT THERE was read at the time as a human draft left
    typed-but-unsubmitted; that attribution NO LONGER STANDS. G-master-0804-2200 (absorbing
    G-master-0804-2203) found the same-day composer content in that same pane was the harness's
    own FAINT ghost-suggestion text — regenerated from session context, surviving Enter by
    design, with nothing typed into the pane at all — so the ghost is the likely culprit for this
    stall too, and an investigator must not re-derive "someone left a draft" from this history.
    The stacking mechanism above holds whichever put the content there, and so does this gate:
    one Enter is sent to flush a submittable draft; a composer still non-empty after that is a
    loud delivery failure, never a silent stall. The harness's own FAINT ghost suggestion is NOT
    a draft and never trips this gate (P35-ghost, G-master-0804-2200 — see composer_real_text):
    it survives Enter by design, so treating it as a draft turned every wake at an idle pane into
    a refusal."""
    if "\n" in text or "\r" in text:
        # s12-03: RETURNED, not printed — the caller prints it — so it goes through the
        # message-building half of `refuse`. Left as a bare literal it would be the ONE un-layered
        # refusal in the file, and invisible to the selftest guard, which scopes to `print(`.
        return False, refusal_text(
            "input",
            "wake text carries a newline, and send-keys delivers a newline as "
            "Enter — the pane's shell would execute the text line by line (G-11). "
            "Write the text to a file and wake with a one-line command that reads it "
            "(see prompt_file).")
    set_injection_context(action="wake")
    if _composer_nonempty(pane):
        ok, err = tmux_send_enter(pane)
        if not ok:
            return False, err
        time.sleep(WAKE_ENTER_VERIFY_DELAY_RETRY)
        if _composer_nonempty(pane):
            return False, ("pane composer holds unsubmitted text that one Enter did not flush — "
                           "wake refused rather than stacking into it (P35-draft)")
    ok, err = tmux_send_text(pane, text)
    if not ok:
        return False, err
    for attempt in range(WAKE_ENTER_ATTEMPTS):
        ok, err = tmux_send_enter(pane)
        if not ok:
            return False, err
        time.sleep(WAKE_ENTER_VERIFY_DELAY_FIRST if attempt == 0 else WAKE_ENTER_VERIFY_DELAY_RETRY)
        if not _wake_unsubmitted(pane, text):
            return True, ""
    return False, (f"Enter did not submit after {WAKE_ENTER_ATTEMPTS} attempt(s) — "
                    f"wake text left unsubmitted in the pane's composer")


PANEL_STRIP_ROWS = 8


def restore_overview_strip(target):
    """After a re-tile, shrink any 'overview' pane in the window back to its strip height."""
    for pid, title in tmux_window_panes(target):
        if title == "overview":
            subprocess.run(["tmux", "resize-pane", "-t", pid, "-y", str(PANEL_STRIP_ROWS)],
                           capture_output=True, text=True)


def tmux_split_pane(target, cwd):
    """Open a tiled pane in the target pane's window. Returns (pane_id, err)."""
    r = subprocess.run(
        ["tmux", "split-window", "-d", "-t", target, "-c", cwd, "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "", r.stderr.strip()
    pane = r.stdout.strip()
    subprocess.run(["tmux", "select-layout", "-t", target, "tiled"], capture_output=True, text=True)
    subprocess.run(["tmux", "set-option", "-w", "-t", target, "pane-border-status", "top"],
                   capture_output=True, text=True)
    restore_overview_strip(target)  # the tiled relayout equalizes; the panel strip stays small
    return pane, ""


def tmux_split_strip(target, cwd, rows=PANEL_STRIP_ROWS):
    """Open a short FULL-WIDTH bottom strip in the target pane's window (not re-tiled).
    Returns (pane_id, err)."""
    r = subprocess.run(
        ["tmux", "split-window", "-d", "-f", "-l", str(rows), "-t", target, "-c", cwd,
         "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "", r.stderr.strip()
    return r.stdout.strip(), ""


def tmux_session_name(target):
    """Session name of a pane ('' when unresolvable)."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", target, "#{session_name}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux_window_panes(target):
    """[(pane_id, pane_title), ...] of the target pane's window."""
    r = subprocess.run(["tmux", "list-panes", "-t", target, "-F", "#{pane_id}\t#{pane_title}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [tuple(ln.split("\t", 1)) for ln in r.stdout.splitlines() if "\t" in ln]


def tmux_new_window(target, name, cwd):
    """Open a named window (tab) in the target pane's session. Returns (pane_id, err)."""
    session = tmux_session_name(target)
    if not session:
        return "", f"cannot resolve session of {target}"
    r = subprocess.run(
        ["tmux", "new-window", "-d", "-t", f"{session}:", "-n", name, "-c", cwd,
         "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "", r.stderr.strip()
    pane = r.stdout.strip()
    subprocess.run(["tmux", "set-option", "-w", "-t", pane, "automatic-rename", "off"],
                   capture_output=True, text=True)
    return pane, ""


def tmux_find_window_pane(session, window):
    """First pane id of `window` in `session`, or "" if that window doesn't exist (or `session`
    is empty). A hit is a valid split-window target; a miss means the window must be created."""
    if not session:
        return ""
    r = subprocess.run(
        ["tmux", "list-panes", "-t", f"{session}:{window}", "-F", "#{pane_id}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return ""
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    return lines[0] if lines else ""


def tmux_kill_pane(pane):
    """Kill a pane; a window whose last pane dies closes with it. Returns (ok, err)."""
    if not is_tmux_pane(pane):
        return False, "not a tmux pane"   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "kill-pane", "-t", pane], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_respawn_pane(pane, cwd):
    """Restart a pane's command IN PLACE — same pane id, same cell, window layout untouched
    (G-12). `-k` kills whatever still runs there first. A renew used to kill the pane and split a
    fresh one, which re-tiles the whole window and destroys an arranged layout. Returns (ok, err)."""
    if not is_tmux_pane(pane):
        return False, "not a tmux pane"   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "respawn-pane", "-k", "-c", cwd, "-t", pane],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def tmux_pane_pid(pane):
    """PID of the pane's own process (its shell), 0 when unresolvable."""
    if not is_tmux_pane(pane):
        return 0   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#{pane_pid}"],
                       capture_output=True, text=True)
    out = r.stdout.strip()
    return int(out) if r.returncode == 0 and out.isdigit() else 0


def tmux_pane_window(pane):
    """Window id (@N) of a pane, '' when unresolvable."""
    if not is_tmux_pane(pane):
        return ""   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#{window_id}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux_pane_window_name(pane):
    """Window NAME of a pane ('control', 'workers'), '' when unresolvable. The id form above
    answers identity; this answers placement, which is what a descriptor declares."""
    if not is_tmux_pane(pane):
        return ""   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#{window_name}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tmux_capture(pane):
    """Full scrollback of a pane, wrapped lines joined. Returns (text, err)."""
    if not is_tmux_pane(pane):
        return "", "not a tmux pane"   # F1: a session-id token is not a tmux target
    r = subprocess.run(["tmux", "capture-pane", "-p", "-J", "-t", pane, "-S", "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return "", r.stderr.strip()
    return r.stdout, ""


def tmux_raise_history_limit():
    subprocess.run(["tmux", "set-option", "-g", "history-limit", HISTORY_LIMIT],
                   capture_output=True, text=True)


