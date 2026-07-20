#!/usr/bin/env bash
#
# Probe for verify_target_listener() in ttyd-serve.sh (batch-08 item 9 part 4, owner ruling
# 2026-07-20). Exercises the guard directly — via sourcing, never by letting ttyd-serve.sh reach
# `tailscale serve` — against real listeners on scratch ports:
#
#   1. empty port            -> expect REFUSE
#   2. foreign listener (nc) -> expect REFUSE, naming what it found
#   3. root-owned ttyd       -> expect REFUSE (mirrors the actual incident: root's `-O login` ttyd)
#   4. ignite's own ttyd     -> expect PASS, on a non-default port (proves the check reads the
#                                configured port, not a hardcoded 7681)
#
# Never touches the packaged `ttyd.service` or any host config — every listener here is started in
# the foreground by this probe and killed at the end (or via the EXIT trap on failure).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IGNITE_ROOT="$(cd "$HERE/../.." && pwd)"
ATTACH_JS="$IGNITE_ROOT/server/pty/ttyd/attach-client.js"

# Source ttyd-serve.sh for verify_target_listener() without ever running main() / tailscale serve —
# main() only fires when the script is executed directly (BASH_SOURCE[0] == $0), not when sourced.
# shellcheck source=/dev/null
source "$HERE/ttyd-serve.sh"
set +e   # ttyd-serve.sh sets -e on source; this probe checks exit codes itself, command by command

PASS=0
FAIL=0
PIDS_TO_KILL=()

cleanup() {
  for p in "${PIDS_TO_KILL[@]:-}"; do
    [[ -n "$p" ]] && kill "$p" >/dev/null 2>&1
  done
  wait >/dev/null 2>&1
}
trap cleanup EXIT

free_port() {
  # Ask the kernel for an ephemeral free TCP port.
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'
}

expect_refuse() {
  local label="$1" port="$2"
  local out rc
  out="$(verify_target_listener "$port" 2>&1)"
  rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "PASS: $label -> refused (exit $rc) as expected"
    echo "  message: $(head -1 <<<"$out")"
    PASS=$((PASS+1))
  else
    echo "FAIL: $label -> guard PASSED, expected REFUSE"
    echo "  output: $out"
    FAIL=$((FAIL+1))
  fi
}

expect_pass() {
  local label="$1" port="$2"
  local out rc
  out="$(verify_target_listener "$port" 2>&1)"
  rc=$?
  if [[ $rc -eq 0 ]]; then
    echo "PASS: $label -> verified as expected"
    echo "  message: $out"
    PASS=$((PASS+1))
  else
    echo "FAIL: $label -> guard REFUSED, expected PASS"
    echo "  output: $out"
    FAIL=$((FAIL+1))
  fi
}

echo "=== 1. empty port ==="
p1="$(free_port)"
expect_refuse "empty port ($p1)" "$p1"

echo
echo "=== 2. foreign listener (bare nc, our own uid) ==="
p2="$(free_port)"
nc -l -p "$p2" >/dev/null 2>&1 &
PIDS_TO_KILL+=("$!")
sleep 0.5
expect_refuse "foreign nc listener (port $p2)" "$p2"
kill "${PIDS_TO_KILL[-1]}" >/dev/null 2>&1; wait "${PIDS_TO_KILL[-1]}" 2>/dev/null

echo
echo "=== 3. root-owned ttyd (mirrors the actual incident: root's -O login ttyd) ==="
p3="$(free_port)"
sudo -n ttyd --interface 127.0.0.1 --port "$p3" -O login >/tmp/probe-root-ttyd.log 2>&1 &
root_ttyd_shell_pid="$!"
sleep 1
expect_refuse "root-owned ttyd -O login (port $p3)" "$p3"
sudo -n pkill -f "ttyd --interface 127.0.0.1 --port $p3" >/dev/null 2>&1
wait "$root_ttyd_shell_pid" 2>/dev/null

echo
echo "=== 4. ignite's own ttyd, on a NON-DEFAULT port (proves the check reads IGNITE_TTYD_PORT, not a hardcoded 7681) ==="
p4="$(free_port)"
ttyd --interface 127.0.0.1 --port "$p4" --credential probe:probe --writable --check-origin --max-clients 1 \
  node "$ATTACH_JS" >/tmp/probe-ignite-ttyd.log 2>&1 &
PIDS_TO_KILL+=("$!")
sleep 1
expect_pass "ignite's own ttyd on non-default port $p4" "$p4"
kill "${PIDS_TO_KILL[-1]}" >/dev/null 2>&1; wait "${PIDS_TO_KILL[-1]}" 2>/dev/null

echo
echo "=== summary: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
