import os
import re
from pathlib import Path

# ---- the CLOSED ADDRESSING RULE for agents (`decisions.md#d-agents-address-owner-not-master`) --
#
# Three lines, and they replace the role-vs-name judgment that measurably drifted (the
# `goal-master` rename incident):
#
#   initiate -> `owner`      the RESERVED bus token for agent-initiated human-bound traffic. The
#                            chat bridge's ferry delivers it under the two ratified gates
#                            (human-interactive seat AND interactive goal), else the row PARKS on
#                            the bus. Delivery is the BRIDGE's business, never this file's: a send
#                            to `owner` is always legal from an agent and always lands in the log.
#   answer   -> the asker    a `to: master` row is legal ONLY as an ANSWER to something master
#                            sent — which on this bus means it carries `--re <n>`.
#   else     -> the NAME     every other address is a seat by name, `channel-master` included:
#                            the restriction is on the ROLE TOKEN, not on the seats holding it.
#
# ⚠ `owner` IS RESERVED AS A SEAT NAME. No seat may be called `owner` — the token must mean the
# human on every bus, and a seat holding it would silently capture owner-bound traffic. Refused at
# check-in (the roster's own door, below) so the name can never enter the roster in the first
# place.
# ---- the ROUTED TYPES (owner ruling D2, 2026-08-19) — the agent NEVER DECIDES WHO TO CONTACT ---
#
# The rule above says WHERE an address is legal. This one says the agent does not pick an address
# at all for two types: it emits a TYPED message to the reserved token `auto` and the SYSTEM routes
# it. The owner's reason is the whole of it — communication is complex, and no agent should have to
# discover who to contact — so the table is encoded HERE, once, and in `coord/communication.md`
# §4 + `coord/roles.md`. It is NEVER written into an agent prompt.
#
#   type     sender                                       -> resolved recipient
#   ------   ------------------------------------------   -------------------------------------
#   stuck    ANY (a seat, or the reconciliation watcher)   `leader`, ALWAYS. The leader escalates
#                                                          to the owner what it cannot solve.
#   ask      a seat whose seat.md says                     `owner`. Its question needs no relay,
#            `human-interactive: yes|true`                 and the existing owner gate below then
#                                                          admits it on its own merits.
#   ask      anyone else                                   `leader`, ALWAYS. The `consultant` chair
#                                                          is deleted [T2-R17, D-7-ruling].
#   *        anyone                                        `auto` is REFUSED. The token is defined
#                                                          only for the routed types; every other
#                                                          type addresses a seat BY NAME.
#
# ⚠ `stuck` IS AUTO-ONLY: naming any recipient but the resolved one is refused, with no `--force`,
# for the same reason the gates below carry none. `ask` KEEPS explicit addressing legal — live
# goals, the kit's own transports and a large number of selftest arms address `ask` by name today,
# and refusing that is a blast radius this change is not scoped to absorb (D8: simplicity over
# completeness). `auto` is taught as THE path in the help text and in the refusals.
#
# ⚠ `auto` IS RESERVED AS A SEAT NAME, exactly as `owner` is and for the same reason: a seat called
# `auto` would silently capture every routed row. Refused at check-in, at the roster's own door.
AUTO_TOKEN = "auto"
ROUTED_TYPES = ("stuck", "ask")
OWNER_TOKEN = "owner"
MASTER_TOKEN = "master"
SUMMARY_MAX = 560
# T2 — a real run logged 305 messages averaging 1,243 chars: an unbounded `read` floods the
# reader's context. A read renders at most this many messages and says how many are still
# waiting; the cursor moves only through what was SHOWN.
READ_LIMIT = 10
DIGEST_SNIPPET = 90   # chars of body rendered per line by `read --digest` / truncated summaries
# T3 — a message body over this many chars is refused (write a file, send its path). --force escapes.
MESSAGE_MAX = 2000
# T5 — broadcast wakes run in a bounded pool: 1.3s of Enter-verify per recipient, serial, made a
# 10-seat send-all cost ~13s of the sender's turn.
WAKE_PARALLEL_MAX = 8

# T6 — two output modes. The DEFAULT is byte-plain (zero escape bytes): the primary reader is an
# agent, and colour codes inside a message body it re-quotes are noise it cannot see. `--pretty`
# (or COORD_PRETTY=1) turns on ANSI colour + aligned columns for the four VIEW commands — status,
# workers, read, pending. It is an EXPLICIT switch, never TTY auto-detection: agents live in TTYs
# too, so a TTY check would hand them the human mode by default (owner ruling, 2026-07-25).
PRETTY = {"on": False}
# W4: an escalation borrows C_RETRACT's bright red — it is the other thing a reader must not miss;
# `queue-request` is engine plumbing and stays dim. D2's `stuck` takes BOLD YELLOW — a reader must
# not miss it, and it must not read as an escalation, which owns the bright red. This dict is the
# SEVENTH copy of the closed vocabulary and moves with the other six: a view meeting a type with no
# colour here raises KeyError on the one row a reader most needs to see. Held closed by
# `server/heart/probes/probe-message-type-vocabulary.js`, which reads all seven and compares them.
C_ALIVE, C_DEAD, C_DONE = "32", "31", "2"   # roster states
C_RETRACT = "1;31"    # supersession markers — the one thing a reader must not miss
C_LOGNOTE = "2;31"    # delivery-failure trailers: the log speaking, not the sender
C_LABEL = "1"         # field labels, agent names, section titles
C_HINT = "2"          # `--` footers and `next:` lines


def c(text, code):
    """ANSI-wrap `text` in --pretty mode; a plain passthrough otherwise. Every colour in this file
    goes through here, so the default output is byte-identical to the uncoloured one."""
    text = str(text)
    if not PRETTY["on"] or not code:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def set_pretty(args):
    """Switch the human mode on from `--pretty` (global or after the subcommand) or COORD_PRETTY.
    Called once by main(); a direct cmd_* caller (watch.py, the self-test) stays plain."""
    env = os.environ.get("COORD_PRETTY", "").strip().lower()
    PRETTY["on"] = bool(getattr(args, "pretty", False)) or env not in ("", "0", "no", "false")
    return PRETTY["on"]

WORKERS_HEADER = (
    "# workers — agent sessions (script-managed, do not edit by hand)\n"
    "\n"
    "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
    "|-------|--------|-----------|------------|------------|-------------|-----------|\n"
)
MESSAGES_HEADER = (
    "# messages — append-only coordination log (script-managed, do not edit by hand)\n"
)
GROUPS_HEADER = (
    "# groups — message groups (script-managed, do not edit by hand)\n"
    "\n"
    "| group | members | created by | created |\n"
    "|-------|---------|------------|---------|\n"
)
GROUP_ROW = re.compile(
    r"^\|\s*(?P<group>[^|]+?)\s*\|\s*(?P<members>[^|]*?)\s*\|\s*(?P<by>[^|]*?)\s*\|\s*(?P<created>[^|]*?)\s*\|$"
)
# T4 — ` | re: N` is ADDITIVE and optional: it sits after `supersedes:` and before the timestamp,
# so every pre-T4 log line still parses with this same regex.
# Every added field is OPTIONAL and the trailing `ts` stays greedy-last, so every log written
# before this grammar existed parses identically — the same additive discipline `re:` was given.
#
# `from-pkg:` is G-94's missing distinguisher. Identity in the log was a NAME, and a name is a
# ROLE: run-1's leader wrote `from: leader | to: leader` INTO run-2's package, and nothing in the
# stored record told the two leaders apart, so run-2's leader filtered it as its own send and the
# cursor stepped past it. A sender that is not a member of the package it is writing INTO now says
# where it came from, which is the ONE fact that makes the two distinguishable at read time.
#
# `why:` is G-100: `append_message` has always written this clause, but the grammar had no group
# for it, so it was absorbed into `ts` and `age_of` returned '?' for every broadcast carrying one.
# Fixed here rather than filed again — this is the exact line being widened, and leaving a known
# unparsed field in a regex while editing it would be perverse.
# `exec:` is the DATED EXECUTION STAMP (7.607 E2b, design-lock item 5) — see `current_execution`.
# OPTIONAL in the grammar, and permanently so: every row written before the stamp existed parses
# with `exec` = None, which is the honest reading (that row predates the delimiter, it does not
# belong to execution `a`). Placed before `why:` so the free-text `why` clause stays the last
# labelled field and its `[^|]*?` cannot swallow a following one.
# W4 adds THREE optional groups, and every one of them sits BEFORE `why:` for the reason the
# paragraph above states about `exec:` — `why` is free text matched `[^|]*?`, so anything placed
# after it is swallowed by that clause. They are the same additive extension `from-pkg:` was, and
# the ferry's by-key header reader (`bus-ferry.js#parseHeader`) already tolerates insertions.
#   `milestone:`     (adv, C41) THE milestone a verdict/escalation belongs to, as its own key.
#                    It succeeds the overloaded `why: milestone-<id>` encoding, which had 2 writers
#                    and 4 readers all pattern-matching a free-text field. DUAL-READ via
#                    `milestone_of`; both are written during the sunset window so every pre-W4 row
#                    and every selftest pinning the old clause keeps answering the same.
#   `chat-thread:` / `deliver:`  (adv, C42) promoted from BODY SIGILS (`[chat-thread: …]`,
#                    `[deliver: post|wake]`) to header mechanics, written by `send --chat-thread` /
#                    `--deliver`. The ferry prefers the header and keeps the body sigils as a
#                    documented fallback — rows already on live buses carry only the bracketed form.
MSG_HEADER = re.compile(
    r"^## (?P<num>\d+) \| from: (?P<sender>\S+)(?: \| from-pkg: (?P<from_pkg>\S+))?"
    r" \| to: (?P<to>\S+) \| type: (?P<type>\S+)"
    r"(?: \| supersedes: (?P<supersedes>\d+))?(?: \| re: (?P<re>\d+))?"
    r"(?: \| exec: (?P<exec_id>\S+))?"
    r"(?: \| milestone: (?P<milestone>\S+))?"
    r"(?: \| chat-thread: (?P<chat_thread>\S+))?"
    r"(?: \| deliver: (?P<deliver>post|wake))?"
    # THE APPROVAL MARK. In grammar order — after `deliver`, BEFORE `why` — for the reason W4's
    # three are: `why`'s `[^|]*?` eats everything after it, so a key placed past it is unreadable.
    # ⚠ AN UNKNOWN KEY DOES NOT REFUSE THIS ROW, IT CORRUPTS IT: with no group of its own the
    # trailing `ts` (`.+`) swallows `| approve-commit: <sha> | <timestamp>` whole and every reader
    # gets a timestamp that is not one. That is why a new writer and this regex land together.
    r"(?: \| approve-commit: (?P<approve_commit>\S+))?"
    r"(?: \| why: (?P<why>[^|]*?))? \| (?P<ts>.+)$"
)
FM_KEY = {
    # roster signature: `seat:` is the KG term (seat.md descriptors); `agent:` is the legacy key
    "agent": re.compile(r"^(?:seat|agent):\s*(\S+)\s*$", re.MULTILINE),
    # 7.278 (C3): the seat's DECLARED agent type, and the capacity term's ONLY source for it.
    # It is read HERE, off the descriptor, and never off `state.json`: the snapshot has no row for
    # a seat that has not launched yet, so sizing the cap from `state_agent_types()` would read
    # EVERY launch candidate as not-counted and the cap could never bind — the class making the
    # answer YES by construction. ABSENT is not `unclassified` and is not a default: the capacity
    # term treats it as outside `counting.counts_toward_cap` (C1 §2.1's literal definition) and
    # NAMES the seat on its own output, per `budget.json`'s `counting.unclassified_with_descriptor`
    # ("never silently counted and never silently skipped"). Ruled `p-7278-wire-form-confirmed`.
    # ⚠ `agent:`'s own pattern is anchored `^(?:seat|agent):`, so it never matched `agent_type:`
    # and this key takes nothing away from it.
    "agent_type": re.compile(r"^agent_type:\s*(\S+)\s*$", re.MULTILINE),
    "harness": re.compile(r"^harness:\s*(\S+)\s*$", re.MULTILINE),
    "model": re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE),
    "effort": re.compile(r"^effort:\s*(\S+)\s*$", re.MULTILINE),
    "cwd": re.compile(r"^cwd:\s*(\S+)\s*$", re.MULTILINE),
    "window": re.compile(r"^window:\s*(\S+)\s*$", re.MULTILINE),
    "ephemeral": re.compile(r"^ephemeral:\s*(\S+)\s*$", re.MULTILINE),
    # dag-11: the seat's HARNESS MODE — `one-shot` | `interactive`. The attest-exit arm gates on
    # THIS DECLARED PROPERTY and never on `harness:`, because harness is a proxy that is true
    # today and breaks the moment an opencode seat runs in TUI mode or a second one-shot harness
    # arrives. Absent means UNDECLARED, which is NOT `one-shot`: the arm refuses rather than
    # assuming, so no existing seat becomes attestable by having said nothing.
    "mode": re.compile(r"^mode:\s*(\S+)\s*$", re.MULTILINE),
    # 7.676 -> D3 (unblock-goals-plan, 2026-08-18): RETIRED. Declared outputs live in ONE
    # surface — the seat.md BODY's io-spec `## Outputs` block, read by `iospec_outputs` (the
    # shared resolver, held equivalent to `envelope/cage-admission.js#parseDeclaredOutputs` by
    # `outputs-resolver-fixtures.json`). This regex survives ONLY as the retirement TRIPWIRE:
    # a descriptor still carrying the key is refused LOUDLY (`_fm_outputs_defect` ->
    # `declared_outputs` at check-out; materialize-seats.py at materialize) — never read as a
    # declaration and never ignored, because a silently-dropped key is an author who believes
    # a contract the kit no longer grades. The two-surface split this closes is the measured
    # 2026-08-18 defect: seats declared in the block were INVISIBLE to this key's readers, and
    # 23 of 26 meet-transcript-summarizer dones graded against nothing.
    "outputs": re.compile(r"^outputs:[ \t]*(.+?)[ \t]*$", re.MULTILINE),
    "observer": re.compile(r"^observer:\s*(\S+)\s*$", re.MULTILINE),
    "auto-wake": re.compile(r"^auto-wake:\s*(\S+)\s*$", re.MULTILINE),
    # r-cos-bounded-inbox / r-engineer-contact — the SENDER BOUND: a comma-separated allow-list of
    # the ONLY seats whose messages reach this one. ABSENT MEANS UNBOUNDED, which is every seat
    # today, so this lands inert and no seat silently loses reachability when it does.
    "senders": re.compile(r"^senders:\s*(.+?)\s*$", re.MULTILINE),
    # G-20's other half, DECLARED instead of named in the kit: which `to: all` TYPES reach this
    # seat. `none` | `all` | a comma-separated type list. ABSENT keeps the built-in default table
    # (broadcast_scope), so every existing package behaves exactly as it does today.
    "broadcast": re.compile(r"^broadcast:\s*(.+?)\s*$", re.MULTILINE),
    # KIT VOCABULARY, deliberately NOT a KG edge — same standing as `senders:`/`broadcast:` above,
    # neither of which is a KG verb either. A seat declaring `relays: master` says it CARRIES the
    # relay path to that role, NOT that it IS one. The distinction is the whole point and was a
    # leader override of this seat's own first proposal (`realizes: master`): `realizes` is the KG's
    # seat->role verb, so it would have said the seat IS a master — and the master role carries
    # READ-EVERYTHING across every goal's threads store plus the universal initiate right. That is a
    # privilege escalation by descriptor, granted as a side effect of fixing an addressing bug.
    # The KG's own v1 stand-in is the authority for a relay instead: "no master agent exists in code
    # — the owner IS the master", so THERE IS NO MASTER SEAT TO REALIZE, only a relay path to a
    # human. The token resolves to whichever seat currently carries it; that seat gains an ADDRESS
    # and gains no scope.
    "relays": re.compile(r"^relays:\s*(.+?)\s*$", re.MULTILINE),
    # THE CORRESPONDENT'S OWN OPT-IN (`ruling-addressable-non-member.md`, constraint 1: derive it,
    # never hardcode a name). A descriptor declaring `addressable: non-member` says THIS AGENT MAY
    # BE ADDRESSED BY A PACKAGE IT IS NOT A MEMBER OF. It is the half a package cannot assert on
    # someone else's behalf: the register (below) supplies only a PATH, and the name, together with
    # the permission, comes from the descriptor the correspondent owns.
    #
    # ⚠ `non-member` IS DESCRIPTIVE, NOT A KG KIND. `sd-graph` resolves no record for
    # `correspondent`, `guest`, `meta-agent`, `non-member` or `external agent`, and PRIN-10 forbids
    # coining one in code — so this reuses the LEADER RULING'S OWN WORDING and mints no term. What
    # to call this kind is an OWNER question, filed, not answered here.
    "addressable": re.compile(r"^addressable:\s*(\S+)\s*$", re.MULTILINE),
    "ctx-refresh": re.compile(r"^ctx-refresh:\s*(\d+)\s*$", re.MULTILINE),
    # G-23 (owner-directed) — `close: mechanical` on a LONG-LIVED seat whose whole state is
    # external and machine-owned. It finishes one session and opens another: no closer agent, no
    # memory.md written or read, no harvest. `ceremony` (the default, and every other value) keeps
    # the full closer ceremony. The two properties this separates — a seat's LIFETIME and its CLOSE
    # PATH — were coupled only by accident of the kit's model: `ephemeral` meant both "short-lived"
    # and "keeps no memory", and the watcher is the case that pulls them apart.
    "close": re.compile(r"^close:\s*(\S+)\s*$", re.MULTILINE),
    # D8 (`one-readiness-predicate`) — THE SEAT'S FALLBACK ARM: what it does when it must reach
    # the owner and the owner is not standing there. Read here for ONE purpose, the check-out hold
    # below; the ferry reads the same key to decide what to do with the row itself.
    # ⚠ `[ \t]*(.+?)[ \t]*$` IS `bus-ferry.js#seatDirFallback`'s PATTERN, BYTE FOR BYTE, and not
    # the `(\S+)` shape of its neighbours here. `fallback: block-and-queue  # ratified 2026-08-09`
    # must read as the SAME WORD to both readers — a value the ferry acts on and this gate cannot
    # see is a seat held for an ask that was never delivered, or released on one that was. `\s` is
    # barred for `outputs:`'s reason above: it matches the NEWLINE and reaches into the next key.
    "fallback": re.compile(r"^fallback:[ \t]*(.+?)[ \t]*$", re.MULTILINE),
}


def _fm_yes(fm, key):
    # ⚠ The quotes are STRIPPED before the compare (r-checkout-selfclose C2, 2026-07-31): the
    # materializer emits `ephemeral: 'yes'` — a YAML dumper MUST quote bare `yes` (it is a YAML
    # boolean), so the quoted form is the NORMAL materialized shape, not an anomaly. Comparing
    # the raw capture left every materialized `ephemeral: 'yes'` reading as False: 41 of run-3's
    # 59 seats carried the flag and 0 parsed as ephemeral — the whole flag class was inert.
    m = FM_KEY[key].search(fm)
    return bool(m) and m.group(1).strip("'\"").lower() in ("yes", "true")


def _fm_mechanical_close(fm):
    """True when the briefing declares `close: mechanical` (G-23). Any other value, and the
    absence of the key, mean the full closer ceremony — the default stays the careful one."""
    m = FM_KEY["close"].search(fm)
    return bool(m) and m.group(1).lower() == "mechanical"


# The three arms a seat may declare, and the one this file acts on. MIRRORED from
# `bus-ferry.js#seatDirFallback` — same vocabulary, same frontmatter-only scope, same strips, same
# "absent, unreadable or outside the vocabulary is no arm at all". NOT a second classification: the
# ferry decides what happens to a `to: owner` ROW on this declaration and the check-out gate below
# decides whether the seat may claim `done` while that row is unanswered. One declaration, two acts.
FALLBACK_ARMS = ("park", "default-and-disclose", "block-and-queue")
FALLBACK_BLOCK_AND_QUEUE = "block-and-queue"


def _fm_fallback(fm):
    """The declared fallback arm, or "" (absent / unreadable / a word outside the vocabulary —
    the ferry's `null` in this file's idiom). The trailing-comment and quote strips are the
    ferry's own, for the reason stated there: `fallback: block-and-queue # ratified …` is
    `block-and-queue` to the `yaml.safe_load` that `component-lint` validates the seat with, so a
    reader without the strip passes lint and reads a word nobody wrote."""
    m = FM_KEY["fallback"].search(fm)
    v = re.sub(r"\s+#.*$", "", m.group(1)).strip().strip("'\"").lower() if m else ""
    return v if v in FALLBACK_ARMS else ""


# ── D8's PARK FORK: WAS THE ASK EVER DELIVERED TO THE OWNER? (owner-ruled 2026-08-11) ──────────
#
# THE RULING. A PARKED ask does not hold the seat. The ferry delivers a `to: owner` row only when
# the goal is in `interactive` execution mode AND the sending seat declares `human-interactive:`;
# otherwise the row PARKS — nobody is told, so nobody can answer, and holding the seat's `done` on
# it is a hold the owner can never clear by answering (`d-parked-ask-autonomous-workaround`: the
# seat proceeds on its authored autonomous workaround and the wave continues).
#
# ⚠⚠ THIS IS A SECOND READING OF THE FERRY'S GATES, AUTHORIZED AS A PINNED MIRROR AND NOTHING ELSE.
# The owner was offered the alternative — have the ferry RECORD delivered/parked on the bus — and
# rejected it: `bus-ferry.js`'s header declares "No gateway intent, no store handle, no listener, no
# write to the bus", and amending that bound is a bigger change than this earns. So coord reads the
# SAME FILES the ferry reads, with the ferry's own rules, and the equality is PINNED BY A SELFTEST
# ROW THAT EXECUTES BOTH READERS OVER ONE SET OF FIXTURES (`D8 pin`, below) — the shape
# `probe-daemon-lane-watch.js` § L0 used for the `after`-cell parser. A mirror nobody checks is the
# drift this whole design deleted; the pin is the part that makes the mirror legitimate.
#
# SOURCE OF TRUTH, mirrored function for function:
#   `supervisor/execution-record.js#askParkedAtGate`  → `ask_parked_at_gate`
#   `bridges/chat/bus-ferry.js#goalExecutionMode` → `goal_execution_mode`   (rung 1 + the rejoin)
#   `bridges/chat/bus-ferry.js#goalKindMode`      → `_goal_kind_mode`       (rung 2)
#   `bridges/chat/bus-ferry.js#seatIsHumanInteractive` → `seat_is_human_interactive`
#   `frontmatterOf` / `isSafeName` / the strips    → `_ferry_frontmatter` / `_ferry_safe_name` /
#                                                    `_ferry_scalar`
#
# ⚠ THE FAIL-SAFE DIRECTION, DECIDED HERE RATHER THAN INHERITED FROM WHICHEVER BRANCH FALLS OUT.
# A cannot-tell READS AS PARKED, i.e. the seat is RELEASED. Three reasons, in order of weight:
#
#   1. THE LADDER IS TOTAL — there is no unresolved state to pick a direction for. Every input
#      lands on `interactive` or `autonomous`: rung 1 the `execution-mode` file, rung 2 `goal.md`'s
#      `goal-kind:`, rung 3 ABSENCE, which the owner's C-4 ruling defines as `autonomous`. And
#      absence is the COMMON case. So "hold when unsure" would not be caution — it would hold every
#      goal that never declared a mode, which is exactly the stall this ruling removes.
#   2. IGNORANCE HERE IS NOT IGNORANCE ABOUT DELIVERY; IT IS THE DELIVERY ANSWER. The gates are a
#      pure function of two files (the ferry writes no marker, by design). An unreadable file is
#      what MAKES the ferry park — it ran the same read, took the same `catch`, and told nobody. To
#      hold on it would be to hold a seat on a row the ferry provably did not send.
#   3. THE OTHER DIRECTION IS NOT REACHABLE HONESTLY ANYWAY: coord would have to disagree with the
#      ferry on inputs where the ferry's answer is KNOWN, which the pin below would then have to
#      encode as an exception — a mirror with a carve-out is the drift, pre-installed.
#
# ⚠ THE RESIDUAL RISK, STATED because the pin cannot see it: the pin runs both readers on ONE
# filesystem, so it proves the RULES agree and cannot prove the BYTES do. The ferry reads on the
# host; a seat's coord reads inside its cage. Both files sit at the package root the cage already
# binds (coord reads `taskforce.csv` and `seats/*/seat.md` from it on every check-out), so a
# divergence would take a binding change — and it would show up as a seat NOT held, with the
# released-note below naming the gate, rather than as silence.
FERRY_INTERACTIVE_MODE = "interactive"
FERRY_AUTONOMOUS_MODE = "autonomous"
# `isSafeName`, verbatim — including its refusal of the reserved `owner` token.
FERRY_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# `frontmatterOf`, verbatim: the FIRST `---`-fenced block, or "" when the file does not open with
# one. NOT `frontmatter_text` above — that reader keeps the opening fence and is byte-matched to
# `discover_workers`'s span. These gates are the FERRY'S question, so they take the ferry's span.
FERRY_FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---")


def _ferry_safe_name(name):
    return bool(FERRY_SAFE_NAME_RE.match(str(name))) and str(name) != OWNER_TOKEN


def _ferry_frontmatter(text):
    m = FERRY_FRONTMATTER_RE.match(str(text))
    return m.group(1) if m else ""


def _ferry_scalar(fm, key):
    """One frontmatter scalar, read the ferry's way: `[ \\t]*(.+?)[ \\t]*$`, then the trailing-`#`
    strip, then the quote strip, then lowercased. "" when absent. Every gate reader in `bus-ferry`
    normalizes this way and the ABSENCE of the strip was a measured defect there (7.626 F3), so it
    is one function here rather than three copies."""
    m = re.search(rf"^{key}:[ \t]*(.+?)[ \t]*$", fm, re.MULTILINE)
    return re.sub(r"\s+#.*$", "", m.group(1)).strip().strip("'\"").lower() if m else ""


def _ferry_read(path):
    """A file the ferry would have read, or None when it could not. `errors="replace"` is not
    laxity: Node's `readFileSync(p, 'utf8')` DECODES invalid bytes to U+FFFD and returns a string,
    where Python would raise — and a raise here would be a Python-only verdict on bytes the ferry
    read happily. Only the errors Node's `catch` sees (ENOENT, EISDIR, EACCES …) return None."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _goal_kind_mode(goal_dir):
    """Rung 2 — the goal's BIRTH ATTRIBUTE, read ONLY when rung 1 found no file. Rung 3 (absence)
    is `autonomous`, the ratified default: a goal nobody declared reachable is not reachable."""
    raw = _ferry_read(Path(goal_dir) / "goal.md")
    kind = "" if raw is None else _ferry_scalar(_ferry_frontmatter(raw), "goal-kind")
    return FERRY_INTERACTIVE_MODE if kind == FERRY_INTERACTIVE_MODE else FERRY_AUTONOMOUS_MODE


def goal_execution_mode(goal_folder):
    """Can this goal talk to the owner at all? The C-4 three-rung ladder (owner-ruled 2026-08-10).

    ⚠ THE WORKSPACE ROUND-TRIP IS MIRRORED, NOT SHORT-CIRCUITED, and it is load-bearing. The JS
    takes `(workspaceRoot, goalId)` and REBUILDS `<ws>/.rbtv/goals/<id>`, where the caller derived
    `<ws>` as `goalFolder/../../..`. For a goal that lives there the trip is an identity; for a
    package ANYWHERE ELSE it resolves to a directory that does not exist, and every rung then falls
    to `autonomous`. Reading `<goal_folder>/execution-mode` directly would be the obvious
    simplification and it would DISAGREE with the ferry on exactly that case — a package outside
    `.rbtv/goals/` is one the ferry's own goal walk never visits, so its asks are never delivered,
    so its seats must never be held. The pin fixtures carry that case."""
    goal_folder = Path(goal_folder)
    if not _ferry_safe_name(goal_folder.name):
        return FERRY_AUTONOMOUS_MODE
    goal_dir = goal_folder.parent.parent.parent / ".rbtv" / "goals" / goal_folder.name
    raw = _ferry_read(goal_dir / "execution-mode")
    if raw is None:
        return _goal_kind_mode(goal_dir)          # the FILE keeps precedence; absence drops a rung
    return (FERRY_INTERACTIVE_MODE if raw.strip().lower() == FERRY_INTERACTIVE_MODE
            else FERRY_AUTONOMOUS_MODE)


def seat_is_human_interactive(goal_folder, seat):
    """Gate 1 — does the SEAT declare itself able to talk to a human? `seats/<seat>/seat.md`
    frontmatter, by PATH, because that is the descriptor the ferry read. Deliberately NOT
    `briefing_frontmatters` (which keys by the DECLARED name and also serves the legacy `workers/`
    layout): where the two disagree — a seat whose folder name is not its declared name — the ferry
    found no file and PARKED, so the honest answer to "was this delivered" is the path read's. That
    mismatch is `component-lint`'s `wrongfolder` defect, not a delivery question."""
    if not _ferry_safe_name(seat):
        return False
    fm = _ferry_read(Path(goal_folder) / "seats" / str(seat) / "seat.md")
    return fm is not None and _ferry_scalar(_ferry_frontmatter(fm),
                                            "human-interactive") in ("yes", "true")


def ask_parked_at_gate(goal_folder, seat):
    """The ferry's own gate NAME when this seat's `to: owner` row PARKS, else "" (delivered).

    The ladder's third rung — `fallback: park` — is deliberately absent here for the JS's reason:
    every caller has already established the arm is `block-and-queue`, so that rung cannot fire.
    "" rather than `None` so the value reads as a reason string throughout; the pin normalizes."""
    if goal_execution_mode(goal_folder) != FERRY_INTERACTIVE_MODE:
        return "execution-mode"
    if not seat_is_human_interactive(goal_folder, seat):
        return "human-interactive"
    return ""


def _fm_window(fm):
    """window: value, normalized — "" (absent/no), "yes" (own window), or a SHARED window
    name (wave layout: seats carrying the same name become panes of one window)."""
    m = FM_KEY["window"].search(fm)
    if not m:
        return ""
    v = m.group(1)
    if v.lower() in ("yes", "true"):
        return "yes"
    if v.lower() in ("no", "false"):
        return ""
    return v


