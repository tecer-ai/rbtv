#!/usr/bin/env python3
"""provider-usage — poll worker-harness plan limits into the control-panel runtime file.

Writes ~/.claude/rbtv-runtime/provider-usage.json for overview-compact.py to render. Sources
(each read-only, each key sent ONLY to its own provider's documented endpoint; keys are never
printed or logged):

  zai      GET https://api.z.ai/api/monitor/usage/quota/limit    (Authorization: <key>, no
           Bearer — Z.AI coding-plan convention). 5h/weekly/MCP quota percentages.
  deepseek GET https://api.deepseek.com/user/balance             (Authorization: Bearer <key>).
           Pay-as-you-go money balance — there is no percentage window.
  codex    LOCAL ONLY: newest ~/.codex/sessions/**/rollout-*.jsonl, last `payload.rate_limits`
           event (primary.used_percent + window_minutes + resets_at, plan_type). Refreshed only
           while a codex session runs — staleness is reported, not hidden. No API calls.
  sakana   No documented balance endpoint (checked 2026-07-24: OpenAI-compatible chat/models
           APIs only) — credits are console-only (console.sakana.ai). Reported as such.

Keys come from opencode's credential store (~/.local/share/opencode/auth.json). Run ad hoc or
let tmux-overview's compact loop refresh it when older than 10 minutes.

  python3 provider-usage.py [--print]      # --print: also pretty-print what was written
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

AUTH = Path.home() / ".local" / "share" / "opencode" / "auth.json"
OUT = Path.home() / ".claude" / "rbtv-runtime" / "provider-usage.json"
CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
TIMEOUT = 10


def auth_key(provider):
    try:
        return (json.load(open(AUTH)).get(provider) or {}).get("key")
    except (OSError, json.JSONDecodeError):
        return None


def get_json(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def zai():
    key = auth_key("zai-coding-plan")
    if not key:
        return {"error": "no credential"}
    try:
        d = get_json("https://api.z.ai/api/monitor/usage/quota/limit", {"Authorization": key})
    except Exception as e:  # noqa: BLE001 — report class only, never the request details
        return {"error": type(e).__name__}
    # Observed shape (2026-07-24): data.limits[] with TOKENS_LIMIT entries — unit 3 + number 5
    # is the 5-hour token window, unit 6 the weekly one; `percentage` = used %, nextResetTime
    # in epoch-ms; data.level = plan tier. TIME_LIMIT entries are tool quotas — skipped.
    data = d.get("data") or {}
    windows = []
    for lim in data.get("limits") or []:
        if lim.get("type") != "TOKENS_LIMIT" or lim.get("percentage") is None:
            continue
        unit, num = lim.get("unit"), lim.get("number")
        label = "5h" if (unit == 3 and num == 5) else ("7d" if unit == 6 else f"u{unit}n{num}")
        reset = lim.get("nextResetTime")
        windows.append({"label": label, "pct": lim["percentage"],
                        "resets_at": int(reset / 1000) if reset else None})
    if not windows:
        return {"error": "no TOKENS_LIMIT windows in response"}
    return {"plan": data.get("level"), "windows": windows}


def deepseek():
    key = auth_key("deepseek")
    if not key:
        return {"error": "no credential"}
    try:
        d = get_json("https://api.deepseek.com/user/balance", {"Authorization": f"Bearer {key}"})
    except Exception as e:  # noqa: BLE001
        return {"error": type(e).__name__}
    infos = d.get("balance_infos") or []
    if not infos:
        return {"error": "no balance_infos"}
    b = infos[0]
    return {"balance": b.get("total_balance"), "currency": b.get("currency"),
            "available": d.get("is_available")}


def codex():
    files = sorted(CODEX_SESSIONS.glob("*/*/*/rollout-*.jsonl"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[:5]:
        last = None
        try:
            for line in open(f, encoding="utf-8"):
                if "rate_limits" not in line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rl = (e.get("payload") or {}).get("rate_limits")
                if isinstance(rl, dict):
                    last = rl
        except OSError:
            continue
        if last:
            out = {"plan": last.get("plan_type"), "as_of": int(f.stat().st_mtime), "windows": []}
            for name in ("primary", "secondary"):
                w = last.get(name)
                if isinstance(w, dict) and w.get("used_percent") is not None:
                    mins = w.get("window_minutes") or 0
                    label = "5h" if mins <= 360 else ("7d" if mins >= 10000 else f"{mins}m")
                    out["windows"].append({"label": label, "pct": w["used_percent"],
                                           "resets_at": w.get("resets_at")})
            return out
    return {"error": "no rate_limits snapshot in recent codex sessions"}


def main():
    data = {"ts": int(time.time()),
            "zai": zai(), "deepseek": deepseek(), "codex": codex(),
            "sakana": {"note": "console-only"}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(OUT)
    if "--print" in sys.argv:
        print(json.dumps(data, indent=1))
    else:
        print(f"written: {OUT}")


if __name__ == "__main__":
    main()
