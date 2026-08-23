#!/usr/bin/env python3
"""gateway_client.py — the coordinate CLI's gateway wire (task 7.57).

Ports, field-for-field, the reference JS client this task was built against:
    ignite/cli/lib/config.js          -> resolve_workspace_root / server_json_path /
                                          read_server_json / select_machine_entry /
                                          resolve_gateway_addr / resolve_token
    ignite/cli/lib/gateway-client.js  -> call_gateway

Stdlib only (coord.py's own module-level-import bar: a third-party import there is a
new hard dependency for every seat on every `coordinate` invocation — the exact outage
shape `save-coord.py` exists to prevent). Wire uses `http.client`, never `requests`.

SCOPE — task 7.57 fork 1 built the CLIENT half only (detection, auth, the wire), because
the gateway had no coordination door to route to. Task 7.93 BUILT that door (owner ruling
`r-793-unbarred-slot-address-door`, 2026-07-30) and this module gained its two calls:
`send_message` (gateway intent `send-message`) and `read_thread` (`inspect messages` by
`thread`). Both are addressed by SLOT/THREAD per the owner's frozen D39/D42 — the thread
CARRIES the address — and mint NO recipient: `d-team-kit-realization`'s divergences (1)
explicit recipient addressing and (4) a stored `to:` column STAND as substrate facts, so
the CLIENT is adapted to the gateway's shape and the gateway is never taught a recipient.

⚠ NOTHING HERE IS EVER REACHED UNLESS THE TRANSPORT IS EXPLICITLY ARMED. coord.py gates
both calls behind `COORD_GATEWAY_TRANSPORT=1`; absent it, no function below is called and
the room's transport is byte-identically what it was (the leader's 7.57 fork-2 ruling: a
naive detect-then-route flips the transport for every seat mid-run).

Credential discipline (inherited from gateway-cli-spec.md, unconditional): the sender
token is read at call time — never cached, never placed in argv or a URL, never logged.
Since 7.566 (mirrored here 2026-08-23, E22) `config.js#resolveToken` reads it from the
environment FIRST and then from the workspace's gitignored `.rbtv/config/sender-token.env`,
walking up from the cwd — the ONE file a seat cage never masks, which is how a CAGED seat
(whose environment carries no token: the daemon's unit ships `EnvironmentFile=-/dev/null`)
gets one at all. `resolve_token` below does the same walk, so `coordinate` can speak to the
gateway from inside a cage exactly as the `ignite` CLI does. A missing token is not raised
here; the request still goes out with no Authorization header, so the gateway's own
AUTH_REFUSED answers, never a client-side fake refusal (config.js's own documented choice).
"""

import http.client
import json
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)


class GatewayUsageError(Exception):
    """A local, never-reaches-the-gateway problem: bad config, bad address, an
    ambiguous server.json. Mirrors CliUsageError (ignite/cli/lib/errors.js)."""


class GatewayTransportError(Exception):
    """The gateway could not be reached, or its response was not valid JSON. Mirrors
    CliTransportError (ignite/cli/lib/errors.js)."""


def resolve_workspace_root(default, env=None):
    """RBTV_IGNITE_WORKSPACE_ROOT env override, else `default`. Mirrors config.js's
    resolveWorkspaceRoot() (which defaults to cwd there); coord.py's own convention is
    a fixed VAULT_ROOT rather than cwd, so the caller supplies that default — this
    module stays free of coord.py's globals (PRIN-11: VAULT_ROOT has one home)."""
    env = os.environ if env is None else env
    override = env.get("RBTV_IGNITE_WORKSPACE_ROOT")
    return Path(override) if override else Path(default)


def server_json_path(workspace_root):
    return Path(workspace_root) / ".rbtv" / "modules" / "ignite" / "server.json"


def read_server_json(workspace_root):
    """The parsed record, or None when no server.json exists yet (never installed for
    this workspace). Malformed JSON is a loud GatewayUsageError, never a silent None —
    mirrors config.js's readServerJson exactly."""
    p = server_json_path(workspace_root)
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GatewayUsageError(
            f"the endpoint record at {p} is not valid JSON — reinstall ignite for this "
            f"workspace, or fix the file by hand ({exc})."
        ) from exc


def select_machine_entry(record, record_path, hostname):
    """record's own machine entry if it names a server, else the one other entry that
    does. Mirrors config.js's selectMachineEntry: server.json is machine-keyed
    (batch-08 item 10, owner-ruled) because it travels via git to every machine."""
    if not isinstance(record, dict):
        return record
    machines = record.get("machines")
    if not isinstance(machines, dict):
        return record  # legacy flat shape — still accepted, same as the JS side

    def has_server(m):
        return (isinstance(m, dict) and isinstance(m.get("tailnet_host"), str)
                and len(m["tailnet_host"]) > 0)

    own = machines.get(hostname)
    if has_server(own):
        return own
    servers = [m for m in machines.values() if has_server(m)]
    if len(servers) == 1:
        return servers[0]
    if len(servers) > 1:
        raise GatewayUsageError(
            f"{record_path} records {len(servers)} machines running a server — ambiguous "
            f"from this machine. Set IGNITE_GATEWAY_ADDR to the gateway you mean."
        )
    return own if own is not None else None


def detect_daemon(workspace_root, hostname=None, env=None):
    """Non-throwing detection: does a daemon serve THIS workspace, on THIS machine, per
    the ruled substrate record? Always safe to call — pure file read, no network.

    Returns a dict, never raises:
        {"detected": False, "reason": "..."}                             -- no record / no machine entry
        {"detected": True, "host": ..., "port": ..., "reason": "..."}    -- a live server is named

    This is the DETECT half of criterion (1), and it is unconditional — Fork 2 (ruled)
    gates the SPEAK half (an actual gateway call) behind explicit opt-in, never this.
    """
    env = os.environ if env is None else env
    hostname = hostname or socket.gethostname()
    p = server_json_path(workspace_root)
    try:
        record = read_server_json(workspace_root)
    except GatewayUsageError as exc:
        return {"detected": False, "reason": str(exc)}
    if record is None:
        return {"detected": False, "reason": f"no endpoint record at {p}"}
    try:
        entry = select_machine_entry(record, p, hostname)
    except GatewayUsageError as exc:
        return {"detected": False, "reason": str(exc)}
    if isinstance(entry, dict) and isinstance(entry.get("tailnet_host"), str) and entry["tailnet_host"]:
        if not isinstance(entry.get("gateway_port"), int):
            return {"detected": False,
                     "reason": f"{p} names a tailnet host but no integer gateway_port"}
        return {"detected": True, "host": entry["tailnet_host"], "port": entry["gateway_port"],
                "reason": f"{p} names a live server for {hostname}"}
    return {"detected": False, "reason": f"{p} has no tailnet address on record for {hostname}"}


def _parse_addr(raw):
    """Accepts a bare `host:port`, a bare host (port 80), or a full URL — mirrors
    config.js's parseAddr, deliberately lenient (gateway-cli-spec.md does not fix the
    env value's exact shape)."""
    value = raw if _SCHEME_RE.match(raw) else f"http://{raw}"
    parts = urlsplit(value)
    if not parts.hostname:
        raise GatewayUsageError(f'IGNITE_GATEWAY_ADDR "{raw}" is not a valid host[:port] or URL')
    port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
    return parts.hostname, port


def resolve_gateway_addr(workspace_root, hostname=None, env=None):
    """(host, port), or raises GatewayUsageError. Mirrors config.js's
    resolveGatewayAddr. Used ONLY when client mode is explicitly attempted — the SPEAK
    half, opt-in per Fork 2 — never by detect_daemon above."""
    env = os.environ if env is None else env
    addr = env.get("IGNITE_GATEWAY_ADDR")
    if addr:
        return _parse_addr(addr)
    info = detect_daemon(workspace_root, hostname=hostname, env=env)
    if info["detected"]:
        return info["host"], info["port"]
    raise GatewayUsageError(
        f"no gateway address configured for this workspace ({info['reason']}). Set "
        f"IGNITE_GATEWAY_ADDR, or run from a workspace where server.json names an "
        f"installed server."
    )


_TOKEN_LINE_RE = re.compile(r"^[ \t]*(?:export[ \t]+)?IGNITE_SENDER_TOKEN[ \t]*=[ \t]*(.*)$", re.M)


def _token_from_env_file(start):
    """Walk up from `start` for `.rbtv/config/sender-token.env` and read IGNITE_SENDER_TOKEN out
    of it — the port of `config.js#readEnvFileToken`: one key, `KEY=value` to end of line, an
    `export ` prefix and surrounding quotes tolerated; the FIRST file found decides (a key-less
    one answers None, it does not keep walking); unreadable/absent → None. Never throws."""
    d = Path(start).resolve() if start is not None else Path.cwd()
    while True:
        try:
            raw = (d / ".rbtv" / "config" / "sender-token.env").read_text(encoding="utf-8")
        except OSError:
            if d.parent == d:
                return None
            d = d.parent
            continue
        m = _TOKEN_LINE_RE.search(raw)
        if not m:
            return None
        value = m.group(1).strip()
        value = re.sub(r"""^(['"])(.*)\1$""", r"\2", value)
        return value or None


def resolve_token(env=None, start=None, workspace_root=None):
    """The sender token, or None. Mirrors `config.js#resolveToken` (7.566): IGNITE_SENDER_TOKEN in
    the environment FIRST; else the workspace's gitignored `.rbtv/config/sender-token.env`, found
    by walking up from `start` (default: the cwd — in a cage, the seat folder) and, when that walk
    finds nothing, from `workspace_root` (coord.py's fixed VAULT_ROOT, which the cwd walk cannot
    reach from a seat folder bound below an ro-masked `seats/`). Never argv, never a URL. A missing
    token is not a local error here: the gateway's own AUTH_REFUSED is the honest answer."""
    env = os.environ if env is None else env
    t = env.get("IGNITE_SENDER_TOKEN")
    if isinstance(t, str) and len(t) > 0:
        return t
    found = _token_from_env_file(start)
    if found is None and workspace_root is not None:
        found = _token_from_env_file(workspace_root)
    return found


# ── task 7.93 · the addressed-message door, client side ────────────────────────────────────────
#
# THE ADDRESS IS THE THREAD (D39/D42: "the thread CARRIES the address"; "addressing is ONE
# recipient field — a slot address OR a groupchat address — v1 collapses it into the thread
# column"). `thread_address` is the ONE place that arithmetic lives, so the send leg and the read
# leg can never disagree about where a message went (PRIN-11).
#
# ⚠ THE ADDRESS IS PACKAGE-SCOPED, and that is correctness rather than decoration: one daemon
# serves a workspace, and two goals both holding a seat named `leader` would otherwise write into
# ONE thread and read each other's mail. The `coord/` prefix additionally guarantees the space can
# never collide with the daemon's own threads (`exec-<n>`, `owner-feed`).
def thread_address(package_name, to, is_group=False):
    """The slot/groupchat address for `to` within `package_name`. Never a recipient column."""
    kind = "groupchat" if (is_group or to == "all") else "slot"
    return f"coord/{package_name}/{kind}/{to}"


def _envelope_error(envelope):
    """The gateway's typed refusal as a string, or None when the envelope reports ok. The HTTP
    status is a courtesy and is never the contract — the envelope is (gateway-cli-spec.md)."""
    if not isinstance(envelope, dict):
        return f"gateway returned a non-object envelope: {envelope!r}"
    if envelope.get("ok") is True:
        return None
    err = envelope.get("error") or {}
    if isinstance(err, dict):
        return f"{err.get('code', 'UNKNOWN')}: {err.get('message', '(no message)')}"
    return f"gateway refused: {err!r}"


def send_message(host, port, thread, mtype, corpus, token=None, timeout=10.0):
    """POST intent `send-message` {type, thread, corpus}. Returns the result dict on success.

    ⚠ RAISES on ANY non-ok outcome — transport error OR a typed refusal. It NEVER returns a value
    that a caller could mistake for a delivery (task 7.94's finding, in this module's own terms: a
    failed call must never read as a successful one). `sender` is deliberately not a parameter:
    the daemon stamps it from the authenticated identity and refuses it from the wire."""
    status, envelope = call_gateway(host, port, "send-message",
                                    {"type": mtype, "thread": thread, "corpus": corpus},
                                    token=token, timeout=timeout)
    err = _envelope_error(envelope)
    if err is not None:
        raise GatewayTransportError(f"send-message refused (HTTP {status}) — {err}")
    return envelope.get("result") or {}


def read_thread(host, port, thread, token=None, timeout=10.0, offset=None, limit=None):
    """`inspect messages` addressed BY THREAD — the read path a tmux seat can actually call.

    The execution-scoped form (`{target:'messages', id:<int>}`) requires a jobs_log exec id, which
    a tmux seat does not have and cannot obtain; that is precisely what 7.57 fork 1 measured and
    ruled NOT MET. Returns the result dict (`rows`, `nextOffset`, `eof`). Raises on any non-ok
    outcome, same discipline as send_message above. An unknown thread is an EMPTY page, not an
    error — a slot legitimately has no messages before its first one."""
    payload = {"target": "messages", "thread": thread}
    if offset is not None:
        payload["offset"] = offset
    if limit is not None:
        payload["limit"] = limit
    status, envelope = call_gateway(host, port, "inspect", payload, token=token, timeout=timeout)
    err = _envelope_error(envelope)
    if err is not None:
        raise GatewayTransportError(f"inspect messages refused (HTTP {status}) — {err}")
    return envelope.get("result") or {}


def secret_add(host, port, name, from_file, token=None, timeout=30.0):
    """POST intent `secret-add` {name, from_file}. Returns (status, envelope).

    The VALUE never crosses this function: only NAME and the drop-file PATH.
    Callers read ok/error off the envelope. sender is stamped by the daemon.
    """
    return call_gateway(host, port, "secret-add",
                        {"name": name, "from_file": from_file},
                        token=token, timeout=timeout)


def call_gateway(host, port, intent, payload, token=None, timeout=10.0):
    """POST / {intent, payload}; returns (status_code, envelope_dict). Mirrors
    gateway-client.js's callGateway: `Authorization: Bearer <token>` when present, JSON
    body, JSON envelope. The HTTP status is a courtesy, never the contract — callers
    read ok/error off the envelope, exactly as the reference client does."""
    body = json.dumps({"intent": intent, "payload": payload}).encode("utf-8")
    headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        try:
            conn.request("POST", "/", body=body, headers=headers)
            res = conn.getresponse()
            raw = res.read()
        except OSError as exc:
            raise GatewayTransportError(f"could not reach gateway at {host}:{port}: {exc}") from exc
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GatewayTransportError(f"gateway response was not valid JSON: {exc}") from exc
        return res.status, envelope
    finally:
        conn.close()
