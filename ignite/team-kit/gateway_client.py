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

SCOPE, deliberately narrow — task 7.57 fork 1, RULED (a): this module proves the CLIENT
half only (detection, auth, the wire). It carries NO coordination send/read logic,
because the gateway has no door for one today: `enqueue-job` with `action_type:
send-message` takes exactly `(type, thread, corpus)` — no recipient field — and
`inspect messages` requires an integer execution id a tmux seat does not have. Building
that door touches the owner-ruled CMP-8 message model and is a successor row, not this
file (see `d-team-kit-realization`, divergences 1 and 4).

Credential discipline (inherited from gateway-cli-spec.md, unconditional): the sender
token is read from the environment ONLY, at call time — never cached, never placed in
argv or a URL, never logged. A missing token is not raised here; the request still
goes out with no Authorization header, so the gateway's own AUTH_REFUSED answers,
never a client-side fake refusal (config.js's own documented choice, inherited as-is).
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


def resolve_token(env=None):
    """IGNITE_SENDER_TOKEN from the environment, or None. Never a file, never argv —
    mirrors config.js's resolveToken exactly: a missing token is not a local error
    here, the gateway's own AUTH_REFUSED is the honest answer (never a client-side
    fake refusal)."""
    env = os.environ if env is None else env
    t = env.get("IGNITE_SENDER_TOKEN")
    return t if isinstance(t, str) and len(t) > 0 else None


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
