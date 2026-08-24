#!/usr/bin/env python3
"""Exclusive flock over <goal>/planning/current/.materialize.lock (spec-planning-door §3)."""

from __future__ import annotations

import os
from pathlib import Path

GOAL_LOCAL_SOURCE = ("planning", "current")
LOCK_NAME = ".materialize.lock"
CODE_LOCK_COLLISION = "lock-collision"


class LockCollision(Exception):
    code = CODE_LOCK_COLLISION

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def current_dir(goal_folder):
    return Path(goal_folder).joinpath(*GOAL_LOCAL_SOURCE)


def lock_path(goal_folder):
    return current_dir(goal_folder) / LOCK_NAME


def pid_is_live(pid):
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _parse(raw):
    pid, pass_id = None, ""
    for line in raw.splitlines():
        if line.startswith("pid="):
            try:
                pid = int(line[4:].strip())
            except ValueError:
                pid = None
        elif line.startswith("pass-id="):
            pass_id = line[8:].strip()
    return pid, pass_id


def read_holder(path):
    try:
        return _parse(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return None, ""


def _payload(pid, pass_id):
    return f"pid={pid}\npass-id={pass_id}\n".encode("utf-8")


class LockHandle:
    def __init__(self, fd, owns, path, pass_id, held_key):
        self._fd = fd
        self._owns = owns
        self.path = path
        self.pass_id = pass_id
        self._held_key = held_key
        self._depth = 1

    def reenter(self):
        self._depth += 1
        return self

    def release(self):
        self._depth -= 1
        if self._depth > 0:
            return
        _held.pop(self._held_key, None)
        if not self._owns or self._fd < 0:
            return
        try:
            import fcntl
            os.ftruncate(self._fd, 0)
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._owns = False
            self._fd = -1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        while self._depth > 0:
            self.release()
        return False


_held = {}


def take_lock(goal_folder, planning_pass_id):
    """Acquire exclusive flock. Same pass-id re-enters; a distinct pass while held refuses.

    Stale = recorded holder pid is not live. Getting the flock after a dead holder is a
    steal, not a C-16 collision. No wall-clock timeout. Same inode: never tmp+replace.
    """
    pass_id = str(planning_pass_id)
    if not pass_id:
        raise ValueError("planning_pass_id is required")
    key = str(Path(goal_folder).resolve())
    existing = _held.get(key)
    if existing is not None:
        if existing.pass_id == pass_id:
            return existing.reenter()
        raise LockCollision(
            f"{lock_path(goal_folder)}: this process already holds pass-id={existing.pass_id!r}"
        )

    cur = current_dir(goal_folder)
    cur.mkdir(parents=True, exist_ok=True)
    path = cur / LOCK_NAME
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            rec_pid, rec_pass = read_holder(path)
            os.close(fd)
            fd = -1
            if rec_pass == pass_id:
                return LockHandle(-1, False, path, pass_id, key)
            raise LockCollision(
                f"{path}: held by pid={rec_pid} pass-id={rec_pass!r} — distinct trigger refused"
            )
        data = _payload(os.getpid(), pass_id)
        os.pwrite(fd, data, 0)
        os.ftruncate(fd, len(data))
        handle = LockHandle(fd, True, path, pass_id, key)
        _held[key] = handle
        fd = -1
        return handle
    finally:
        if fd >= 0:
            os.close(fd)
