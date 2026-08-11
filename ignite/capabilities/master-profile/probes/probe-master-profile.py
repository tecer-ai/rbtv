#!/usr/bin/env python3
"""probe-master-profile.py — the daemon half of the master-profile knob, proven against a COPY.

NOTHING HERE TOUCHES THE LIVE BRIDGE CONFIG OR THE LIVE UNIT. Every act runs under `tempfile` on a
byte-copy of `.rbtv/config/chat-bridge-config.json`, and the restart is a STUB the module is pointed
at (`mod.DAEMON_OPERATOR`). The real one restarts `rbtv-chat-bridge`, which would end the owner's
live conversation — a probe may not cost that.

  1. THE HAPPY PATH LANDS — a staged `{"master-profile": "claude-opus"}` rewrites the field in the
     COPY, and re-reading the FILE answers `claude-opus`. Read from the file, never from the record.
  2. THE RESTART IS INVOKED AT THE BRIDGE, AND IT IS THE LAST ACT — the stub records its argv
     (`restart --service chat-bridge`, never `--service ignite`: restarting the wrong unit would
     leave the bridge on the old profile and read as a success) AND snapshots the config as it
     stood when it ran, which must already carry the new value.
  3. AN UNKNOWN PROFILE IS REFUSED AND THE FILE IS BYTE-IDENTICAL — the refusal names the live
     `profiles:` set, and no restart fires. This is the check the whole capability turns on: an
     unknown name does NOT fail at the bridge, it fails at the SPAWN, one owner message later,
     with the sitting already accounted for.
  4. VALIDATION READS THE LIVE ROSTER, NOT A FROZEN LIST — a profile added to a COPY of
     spawn-profiles.yaml is accepted when validated against that copy and refused against a copy
     with it removed. A hard-coded roster passes check 3 and fails here.
  5. AN ABSENT KEY REFUSES RATHER THAN BEING CREATED — with `master_profile` deleted, `show`
     reports the `session_profile` fallback and names it, and `apply` refuses without writing.
     Creating the key would split master and session traffic apart without anyone deciding to.
  6. THE SURGICAL-EDIT CONTROL — exactly one line changes, and the one-space indentation of the
     hand-authored document survives (a `json.dump` round trip would rewrite every line).
  7. THE MUTANT — the membership check is neutered in a copy of the module source and check 3 is
     re-run. It MUST now be accepted; otherwise check 3 is scoring nothing and this probe exits 2
     INOPERATIVE rather than reporting a pass it did not earn.
  8. THE REGISTERED ARGV ITSELF — the argv `config/spawn-profiles.yaml` declares for
     `tools: master-profile`, read out of that file and run as a SUBPROCESS with only the
     live-state operands substituted. Added after the twin capability's first live fire died on
     `error: unrecognized arguments: --config` with every function-level check green: the daemon
     execs a command line, and a check that only calls the function never sees it.
  9. THE SELF-REPORT REACHES THE OWNER'S THREAD, AND IT PRECEDES THE RESTART — `request
     --chat-thread` stages the id and a token the ferry could not route refuses at request time;
     `apply` on a threaded request appends EXACTLY ONE `to: owner` row, parsed back the way
     `bus-ferry.js` parses it (fields BY KEY) and carrying the BRACKETED token; the restart stub's
     snapshot of the bus already holds that row, which is what discriminates report-then-restart
     from restart-then-report; a request with NO token appends nothing at all; and a REFUSED
     request with a token reports its refusal, because "your switch did not happen, and here is
     why" is the answer the owner is owed most.
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tool" / "master_profile.py"
LIVE_PROFILES = Path(__file__).resolve().parents[3] / "config" / "spawn-profiles.yaml"
# The live bridge config is taken from the TOOL's own resolution (`mod.DEFAULT_CONFIG`), not
# recomputed here: two spellings of the same path is how a probe ends up proving a file the tool
# never reads. Bound at the top of main(), once the module is loaded.
LIVE_CONFIG = None

failures: list[str] = []
inoperative: list[str] = []


def registered_argv(entry):
    """The argv the LIVE `config/spawn-profiles.yaml` declares for one `tools:` entry.

    Read from the config rather than retyped here: a retyped copy proves the probe author's memory
    of the entry, which is the very thing that was wrong."""
    import re as _re
    lines = LIVE_PROFILES.read_text(encoding="utf-8").splitlines()
    at = next((i for i, ln in enumerate(lines) if ln.rstrip() == f"  {entry}:"), None)
    if at is None:
        return None
    out, seen_argv = [], False
    for ln in lines[at + 1:]:
        if ln.strip() and not ln.startswith("    ") and not ln.lstrip().startswith("#"):
            break
        if ln.rstrip() == "    argv:":
            seen_argv = True
            continue
        s = ln.strip()
        if seen_argv and s.startswith("- "):
            out.append(s[2:].strip().strip('"').strip("'"))
        elif seen_argv and s and not s.startswith("#"):
            break
    return out or None


def load(path, name="mp"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stub_operator(tmp, target, bus=None):
    """A stand-in for `rbtv-ignite-daemon` that records its argv and snapshots what the state
    looked like WHEN IT RAN. `bus` adds a second snapshot — the coordination log — which is how
    check 9 discriminates report-then-restart from restart-then-report. Guarded, because on every
    other check the bus file legitimately does not exist and a missing file is not a failure."""
    rec, snap = tmp / "restart.argv", tmp / "restart.snapshot"
    bus_snap = tmp / "restart.bus-snapshot"
    s = tmp / "stub-daemon-operator"
    s.write_text("#!/usr/bin/env bash\n"
                 f'printf "%s\\n" "$*" >> {rec}\n'
                 f'cp {target} {snap}\n'
                 + (f'cp {bus} {bus_snap} 2>/dev/null || true\n' if bus else ""),
                 encoding="utf-8")
    s.chmod(0o755)
    return s, rec, snap


# `## 4774 | from: master-profile | to: owner | type: note | exec: 2026-08-10a | 2026-08-10 14:23`
#
# READ THE FIELDS BY KEY, NEVER BY POSITION — `bus-ferry.js#parseHeader`'s own discipline, and the
# reason it has it: the bus header grammar is ADDITIVE, `from-pkg:` and `exec:` already sit between
# the fixed fields, and a positional regex reads such a row as malformed and drops it silently.
BUS_HEADER_RE = re.compile(r"^## (\d+) \| (.+)$")


def bus_rows(bus):
    """Every row of a coordination log, keyed exactly as the ferry keys them."""
    if not Path(bus).is_file():
        return []
    rows, cur = [], None
    for line in Path(bus).read_text(encoding="utf-8").split("\n"):
        m = BUS_HEADER_RE.match(line)
        if m:
            fields = {}
            for part in m.group(2).split(" | "):
                i = part.find(": ")
                if i > 0:
                    fields[part[:i]] = part[i + 2:].strip()
            cur = {"id": int(m.group(1)), "fields": fields, "body": []}
            rows.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    for r in rows:
        r["body"] = "\n".join(r["body"]).strip()
    return rows


def stage(inbox, payload, name="a.json"):
    inbox.mkdir(parents=True, exist_ok=True)
    p = inbox / name
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return p


def check(cond, msg):
    if not cond:
        failures.append(msg)
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")


def main():
    global LIVE_CONFIG
    mod = load(TOOL)
    LIVE_CONFIG = Path(mod.DEFAULT_CONFIG)

    if not LIVE_CONFIG.is_file():
        inoperative.append(f"the live bridge config {LIVE_CONFIG} does not resolve — this probe "
                           f"copies it as its fixture, and a fabricated one would prove nothing "
                           f"about the shape actually shipped")
        print(f"probe-master-profile: INOPERATIVE — {inoperative}")
        return 2

    # ── 1, 2, 6 ─────────────────────────────────────────────────────────────────────────────
    print("check 1/2/6 — happy path lands, the BRIDGE is restarted last, one line moved")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        cfg = tmp / "chat-bridge-config.json"
        shutil.copy2(LIVE_CONFIG, cfg)
        before_lines = cfg.read_text(encoding="utf-8").splitlines()
        inbox = tmp / "inbox"
        stub, rec, snap = stub_operator(tmp, cfg)
        mod.DAEMON_OPERATOR = stub

        stage(inbox, {"master-profile": "claude-opus"})
        out = mod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)

        check(out["ok"] is True, "the fire reports ok")
        got = mod.read_value(cfg)
        check(got["profile"] == "claude-opus" and got["source"] == "explicit",
              f"re-reading the config file answers claude-opus/explicit (got "
              f"{got['profile']}/{got['source']})")
        check(rec.exists() and "restart --service chat-bridge" in rec.read_text(),
              f"the restart was invoked at the BRIDGE unit "
              f"({rec.read_text().strip() if rec.exists() else '<never ran>'})")
        check(rec.exists() and "--service ignite" not in rec.read_text(),
              "and never at the ignite unit")
        check(snap.exists() and "claude-opus" in snap.read_text(),
              "the config AS THE RESTART SAW IT already carried the new value — edit precedes restart")

        after_lines = cfg.read_text(encoding="utf-8").splitlines()
        diff = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
        check(len(before_lines) == len(after_lines) and len(diff) == 1,
              f"exactly one line changed, line count unchanged (changed={len(diff)})")
        check(bool(diff) and after_lines[diff[0]].startswith(before_lines[diff[0]][:2]),
              "and the document's own indentation survived (no json.dump round trip)")

        settled = sorted((inbox / "done").glob("*.outcome.json"))
        check(len(settled) == 1 and json.loads(settled[0].read_text())["outcome"] == "ACCEPTED",
              "one ACCEPTED outcome record settled where the requester can read it")

    # ── 3 ───────────────────────────────────────────────────────────────────────────────────
    print("check 3 — an unknown profile refuses, names the live set, and writes nothing")
    for label, payload in (("unknown-name", {"master-profile": "gpt-9-ultra"}),
                           ("empty-name", {"master-profile": ""}),
                           ("non-string", {"master-profile": 5}),
                           ("wrong-shape", {"profile": "claude-opus"})):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = tmp / "chat-bridge-config.json"
            shutil.copy2(LIVE_CONFIG, cfg)
            digest = sha(cfg)
            inbox = tmp / "inbox"
            stub, rec, snap = stub_operator(tmp, cfg)
            mod.DAEMON_OPERATOR = stub
            stage(inbox, payload)
            out = mod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)
            recs = sorted((inbox / "refused").glob("*.outcome.json"))
            stated = json.loads(recs[0].read_text())["stated-refusal"] if recs else None
            check(out["ok"] is False and sha(cfg) == digest and not rec.exists() and stated,
                  f"{label}: refused, config sha unchanged, no restart, requester-readable — "
                  f"{(stated or '<no record>')[:90]}")
            if label == "unknown-name":
                check(stated is not None and "claude-fable" in stated,
                      "the unknown-name refusal names the live profile set back to the requester")

    # ── 4 ───────────────────────────────────────────────────────────────────────────────────
    print("check 4 — the roster is read live, not frozen in the tool")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        text = LIVE_PROFILES.read_text(encoding="utf-8")
        # A profile name that CANNOT be in any shipped roster.
        added = tmp / "with-invented.yaml"
        added.write_text(text.replace("profiles:\n", "profiles:\n  invented-probe-profile:\n", 1),
                         encoding="utf-8")
        removed = tmp / "without-sonnet.yaml"
        removed.write_text(text.replace("\n  claude-sonnet:\n", "\n  claude-sonnet-renamed:\n", 1),
                           encoding="utf-8")
        ok_added = False
        try:
            mod.validate("invented-probe-profile", added)
            ok_added = True
        except mod.Refusal:
            pass
        check(ok_added, "a profile present only in a COPY of spawn-profiles.yaml is accepted "
                        "against that copy — the list is read, not hard-coded")
        refused_removed = False
        try:
            mod.validate("claude-sonnet", removed)
        except mod.Refusal:
            refused_removed = True
        check(refused_removed, "and a profile absent from a copy is refused against it")

    # ── 5 ───────────────────────────────────────────────────────────────────────────────────
    print("check 5 — an absent master_profile refuses rather than being created")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        cfg = tmp / "chat-bridge-config.json"
        text = LIVE_CONFIG.read_text(encoding="utf-8")
        stripped = "\n".join(l for l in text.splitlines() if '"master_profile"' not in l) + "\n"
        check(stripped != text, "the fixture removed the master_profile line")
        cfg.write_text(stripped, encoding="utf-8")
        digest = sha(cfg)

        v = mod.read_value(cfg)
        expect = json.loads(cfg.read_text())["session_profile"]
        check(v["source"] == "session_profile-fallback" and v["profile"] == expect,
              f"show reports the session_profile fallback by name — {expect} "
              f"(got {v['source']}/{v['profile']})")

        inbox = tmp / "inbox"
        stub, rec, snap = stub_operator(tmp, cfg)
        mod.DAEMON_OPERATOR = stub
        stage(inbox, {"master-profile": "claude-opus"})
        out = mod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)
        check(out["ok"] is False and sha(cfg) == digest and not rec.exists(),
              "apply refused, wrote nothing, and restarted nothing")

    # ── 7 THE MUTANT ────────────────────────────────────────────────────────────────────────
    print("check 7 — the mutant: neuter the membership check and the unknown name MUST be accepted")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = TOOL.read_text(encoding="utf-8")
        mutant_src = src.replace("    if name not in known:", "    if False:", 1)
        if mutant_src == src:
            inoperative.append("the mutation target `if name not in known:` was not found in the "
                               "tool source — the mutant proves nothing and check 3 is unscored")
        else:
            # The mutant is nested deep enough that the module's own
            # `Path(__file__).resolve().parents[N]` derivations still resolve — a mutant that
            # cannot IMPORT is not evidence, it is a crash wearing a red verdict.
            mdir = tmp.joinpath(*[f"x{i}" for i in range(8)])
            mdir.mkdir(parents=True)
            mpath = mdir / "mutant.py"
            mpath.write_text(mutant_src, encoding="utf-8")
            mmod = load(mpath, "mp_mutant")
            cfg = tmp / "chat-bridge-config.json"
            shutil.copy2(LIVE_CONFIG, cfg)
            inbox = tmp / "inbox"
            stub, rec, snap = stub_operator(tmp, cfg)
            mmod.DAEMON_OPERATOR = stub
            stage(inbox, {"master-profile": "gpt-9-ultra"})
            out = mmod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)
            if not (out["ok"] and mmod.read_value(cfg)["profile"] == "gpt-9-ultra"):
                inoperative.append("the mutant did NOT go green — check 3's refusal is not being "
                                   "produced by the membership check, so check 3 scores nothing")
            print("  ok   the mutant accepted gpt-9-ultra — check 3 is discriminating")

    # ── 8 THE REGISTERED ARGV ITSELF ──────────────────────────────────────────────────────
    #
    # ⚠ THIS ARM EXISTS BECAUSE ITS ABSENCE COST A LIVE FIRE. Every check above calls `apply()` as a
    # PYTHON FUNCTION, which is exactly the surface the daemon never touches: the daemon execs the
    # wrapper with the argv `config/spawn-profiles.yaml` declares. `--config` was a ROOT option and
    # that argv puts it after the verb, so the first real fire died with
    # `error: unrecognized arguments: --config …`, drained nothing, and recorded `failed` — while
    # every function-level check stayed green. A check that cannot see the caller's shape is not
    # checking the caller.
    #
    # So: read THIS capability's own `tools:` entry out of the live config, substitute only the two
    # paths that must not point at live files, and run the wrapper as a SUBPROCESS.
    print("check 8 — the argv the `tools: master-profile` entry actually declares, run as a subprocess")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        argv = registered_argv("master-profile")
        if argv is None:
            inoperative.append("the live spawn-profiles.yaml carries no `tools: master-profile` entry — "
                               "the one surface the daemon uses is unchecked")
        else:
            inbox = tmp / "inbox"
            inbox.mkdir()
            stage(inbox, {"master-profile": "claude-haiku"})
            cfg = tmp / "chat-bridge-config.json"
            shutil.copy2(LIVE_CONFIG, cfg)
            # Substitute ONLY the operands that would point at live state. Every other token —
            # including the interpreter, the script path, the verb, and the flag SPELLINGS and
            # ORDER — is the config's own, byte for byte.
            run_argv = list(argv)
            for i, tok in enumerate(run_argv):
                if i and run_argv[i - 1] == "--inbox":
                    run_argv[i] = str(inbox)
                elif i and run_argv[i - 1] == "--config":
                    run_argv[i] = str(cfg)
            env = dict(os.environ)
            # A unit the user manager has never heard of: `daemon-operator` refuses it (exit 1) and
            # drives NOTHING, so the real restart leg is exercised as far as it can be without
            # touching a live service.
            env["RBTV_IGNITE_UNIT"] = "rbtv-probe-no-such-unit-master-profile.service"
            r = subprocess.run(run_argv, capture_output=True, text=True, env=env)
            check(r.returncode == 0,
                  f"the registered argv runs clean (exit {r.returncode}) — "
                  f"{(r.stderr.strip().splitlines() or [''])[-1][:120]}")
            check(mod.read_value(cfg)["profile"] == "claude-haiku",
                  "and the edit it was fired to make landed in the copy")

    # ── 9 THE SELF-REPORT INTO THE OWNER'S OWN CHAT THREAD ────────────────────────────────
    #
    # ⚠ THE INBOX SHAPE IS PART OF THE FIXTURE. The tool DERIVES the bus from the inbox
    # (`<goal>/settings-requests/<capability>` → `<goal>/coordination`) rather than naming a goal,
    # so a flat temp inbox would prove a path the daemon never takes — and a probe that named the
    # live goal would append to the owner's real bus, which a read-only check may not do.
    print("check 9 — the outcome reports itself into the owner's thread, BEFORE the restart")
    THREAD = "C0PROBEMP:1754812345.123456"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inbox = tmp / "goal" / "settings-requests" / "master-profile"
        bus = tmp / "goal" / "coordination" / "messages.md"
        cfg = tmp / "chat-bridge-config.json"
        shutil.copy2(LIVE_CONFIG, cfg)
        stub, rec, snap = stub_operator(tmp, cfg, bus=bus)
        mod.DAEMON_OPERATOR = stub

        # `/bin/true` stands in for the `ignite` client: `request` stages BEFORE it enqueues, and
        # what is under test here is the payload, not the queue.
        out = mod.request(inbox, "claude-opus", "/bin/true", profiles_path=LIVE_PROFILES,
                          chat_thread=THREAD)
        staged = json.loads(Path(out["staged"]).read_text())
        check(staged.get("chat-thread") == THREAD,
              f"request --chat-thread stages the id in the payload (got {staged.get('chat-thread')!r})")
        bad_refused = False
        try:
            mod.request(inbox, "claude-opus", "/bin/true", profiles_path=LIVE_PROFILES,
                        chat_thread="C0PROBEMP-1754812345")
        except mod.Refusal:
            bad_refused = True
        check(bad_refused, "a token bus-ferry.js could not route refuses in the sitting that typed it")

        prev = mod.read_value(cfg)["profile"]
        mod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)
        rows = bus_rows(bus)
        check(len(rows) == 1, f"exactly ONE bus row was appended (got {len(rows)})")
        if rows:
            f, body = rows[0]["fields"], rows[0]["body"]
            check(f.get("from") == "master-profile" and f.get("to") == "owner"
                  and f.get("type") == "note",
                  f"and its header carries from/to/type the ferry requires ({f})")
            check(f"[chat-thread: {THREAD}]" in body,
                  "the BRACKETED token is in the body — the plain form does not route")
            check("[deliver: post]" in body,
                  "an ACCEPTED outcome asks to be POSTED verbatim — nothing to act on")
            check(f"`{prev}` → `claude-opus`" in body,
                  f"the body states the change as old → new (`{prev}` → `claude-opus`)")
            check("NEW threads only" in body, "and carries the thread-scope line the owner needs")
            check(not any(l.startswith("|") or l.startswith("#") for l in body.split("\n")),
                  "the body is mrkdwn — no pipe tables, no markdown headings")
        check(bus.read_text(encoding="utf-8").endswith("\n"),
              "the log ends with a newline — the ferry's torn-write rule only counts a row that does")
        check((tmp / "restart.bus-snapshot").is_file()
              and THREAD in (tmp / "restart.bus-snapshot").read_text(),
              "the bus AS THE RESTART SAW IT already carried the report — report precedes restart")

    print("check 9b — a request with NO chat thread reports nothing at all")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inbox = tmp / "goal" / "settings-requests" / "master-profile"
        bus = tmp / "goal" / "coordination" / "messages.md"
        cfg = tmp / "chat-bridge-config.json"
        shutil.copy2(LIVE_CONFIG, cfg)
        stub, rec, snap = stub_operator(tmp, cfg, bus=bus)
        mod.DAEMON_OPERATOR = stub
        stage(inbox, {"master-profile": "claude-opus"})
        out = mod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)
        check(out["ok"] and not bus.exists(),
              "the switch landed and no bus row exists — an untokened request is silent, as before")

    print("check 9c — a REFUSED outcome carrying a thread reports its refusal too")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inbox = tmp / "goal" / "settings-requests" / "master-profile"
        bus = tmp / "goal" / "coordination" / "messages.md"
        cfg = tmp / "chat-bridge-config.json"
        shutil.copy2(LIVE_CONFIG, cfg)
        digest = sha(cfg)
        stub, rec, snap = stub_operator(tmp, cfg, bus=bus)
        mod.DAEMON_OPERATOR = stub
        stage(inbox, {"master-profile": "gpt-9-ultra", "chat-thread": THREAD})
        out = mod.apply(inbox, cfg, profiles_path=LIVE_PROFILES)
        rows = bus_rows(bus)
        check(out["ok"] is False and sha(cfg) == digest and not rec.exists(),
              "the refusal still refuses — config untouched, no restart")
        check(len(rows) == 1 and "REFUSED" in rows[0]["body"]
              and f"[chat-thread: {THREAD}]" in rows[0]["body"],
              f"and exactly one row reports the refusal into the thread (got {len(rows)} row(s))")
        check(bool(rows) and "[deliver: wake]" in rows[0]["body"],
              "and a REFUSED outcome asks to WAKE an agent — the refusal needs follow-up "
              "(owner ruling 2026-08-10: post always, wake when agent action is needed)")

    if inoperative:
        print(f"probe-master-profile: INOPERATIVE — {inoperative}")
        return 2
    if failures:
        print(f"probe-master-profile: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-master-profile: PASS — the edit lands, the BRIDGE restart is the last act, "
          "unknown names refuse against the LIVE roster leaving the file byte-identical, an absent "
          "key refuses rather than being created, and the membership check is proven discriminating "
          "by mutation — the argv the daemon actually fires runs clean as a subprocess, and a "
          "request naming its chat thread reports its outcome (accepted OR refused) as exactly one "
          "ferry-parseable bus row written BEFORE the restart")
    return 0


class _Tee:
    def __init__(self, real):
        self.real, self.buf = real, []

    def write(self, s):
        self.real.write(s)
        self.buf.append(s)
        return len(s)

    def flush(self):
        self.real.flush()


if __name__ == "__main__":
    tee = _Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    finally:
        sys.stdout = tee.real
        Path(__file__).with_suffix(".out").write_text("".join(tee.buf), encoding="utf-8")
    sys.exit(rc)
