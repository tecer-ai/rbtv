"""Exclusive advisory lock on an open file descriptor — Linux AND Windows.

POSIX uses `fcntl.flock`. Windows has no fcntl, so it locks one byte with
`msvcrt.locking`, far past any content, so another handle can still READ the
file while it is held (a claim file is read by the live-claims probe). The
descriptor's position is restored, so a caller's next write lands where it
expects.
"""

from __future__ import annotations

import os
import time

if os.name == "nt":
    import msvcrt

    _BYTE = 1 << 30

    def _at_lock_byte(fd: int, mode: int) -> None:
        pos = os.lseek(fd, 0, os.SEEK_CUR)
        os.lseek(fd, _BYTE, os.SEEK_SET)
        try:
            msvcrt.locking(fd, mode, 1)
        finally:
            os.lseek(fd, pos, os.SEEK_SET)

    def try_lock(fd: int) -> bool:
        try:
            _at_lock_byte(fd, msvcrt.LK_NBLCK)
        except OSError:
            return False
        return True

    def unlock(fd: int) -> None:
        _at_lock_byte(fd, msvcrt.LK_UNLCK)

else:
    import fcntl

    def try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def lock(fd: int) -> None:
    """Block until the lock is held."""
    while not try_lock(fd):
        time.sleep(0.05)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "x.lock")
        a = os.open(path, os.O_RDWR | os.O_CREAT)
        b = os.open(path, os.O_RDWR)
        os.write(a, b"body")
        assert try_lock(a)
        assert not try_lock(b), "second handle must not take a held lock"
        with open(path, encoding="utf-8") as f:
            assert f.read() == "body", "a held lock must not block reads"
        assert os.lseek(a, 0, os.SEEK_CUR) == 4, "position must be restored"
        unlock(a)
        assert try_lock(b)
        unlock(b)
        os.close(a)
        os.close(b)
    print("file_lock selftest: ok")
