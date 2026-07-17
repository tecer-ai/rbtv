#!/usr/bin/env python3
# The dtach attach BRIDGE (session-surface-spec.md Design 2 — "the daemon is a socket CLIENT;
# keys, capture, and the watch-tee attach and RE-attach at will").
#
# WHY A BRIDGE (a disk-proven necessity, recorded at 6.2): the design assumed the daemon could be
# a plain `dtach -a` client and read its stdout. MEASURED FALSE this task — `dtach -a` REFUSES
# non-terminal stdio: "Attaching to a session requires a terminal." So the daemon cannot pipe
# `dtach -a` directly. This bridge allocates a pty for `dtach -a` (via pty.fork), sets a fixed
# winsize so the holder's pty renders at a sane size, and relays:
#     daemon stdin  -> pty master  -> dtach -> holder pty  (KEYSTROKES, the POST /keys/:id rung)
#     holder pty -> dtach -> pty master -> daemon stdout    (SCREEN byte stream -> vt model + log tee)
#
# It uses dtach's OWN battle-tested client (no reimplementation of dtach's socket protocol) and
# adds NO npm dependency: python3 is a system tool the daemon invokes like systemctl/dtach/bwrap.
# It is DISPOSABLE and RE-ATTACHABLE: the pty master lives in the in-unit holder, never here, so
# this process dying does NOT end the session — a daemon restart re-spawns the bridge and the
# session genuinely survives (spec Behavior #7). `-r winch` makes dtach request a repaint on
# attach, so the vt model rebuilds after a reconnect (Design 2 caveat 2).
#
# Usage: pty-bridge.py <socket-path> [rows] [cols]
import os
import sys
import pty
import select
import struct
import fcntl
import termios

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: pty-bridge.py <socket> [rows] [cols]\n")
        return 2
    sock = sys.argv[1]
    rows = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 80

    pid, fd = pty.fork()
    if pid == 0:
        # Child: become dtach's attach client on the pty slave. -E disables the escape char (no
        # ctrl-\ detach injection into the byte stream); -r winch asks the program to repaint on
        # attach (a fresh vt model rebuilds on reconnect).
        try:
            os.execvp("dtach", ["dtach", "-a", sock, "-E", "-r", "winch"])
        except OSError as exc:
            sys.stderr.write("dtach exec failed: %s\n" % exc)
        os._exit(127)

    # Parent: fix the pty winsize so the holder's program renders at rows x cols.
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except OSError:
        pass

    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()
    # Make stdin non-blocking is unnecessary; select gates reads. Relay until the master closes
    # (holder pty gone -> session ended) or our stdin closes (daemon detached us).
    open_fds = [fd, stdin_fd]
    try:
        while True:
            r, _, _ = select.select(open_fds, [], [], 1.0)
            if fd in r:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    break
                if not data:
                    break  # master EOF -> session ended
                try:
                    os.write(stdout_fd, data)
                except OSError:
                    break
            if stdin_fd in r:
                try:
                    keys = os.read(stdin_fd, 65536)
                except OSError:
                    keys = b""
                if not keys:
                    # daemon closed our stdin -> detach cleanly, leave the session alive
                    open_fds = [fd]
                    continue
                try:
                    os.write(fd, keys)
                except OSError:
                    break
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
