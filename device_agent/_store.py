"""Shared JSON-file storage for policy.py and pending_actions.py.

Everything that touches this store - the touchscreen UI (desktop
autostart), cli_approve.py (SSH), and device-agent.service - runs as the
same Linux user (pi), so a plain per-user directory is always writable and
always the same directory for all three; there's no need for a
system-wide location with its own permission setup, and no risk of two
processes silently disagreeing about which file they're reading.

Writes go to a temp file in the same directory and are then renamed into
place (os.replace is atomic on POSIX), so a crash or power loss mid-write -
plausible on a Pi with no UPS - can't leave a truncated/corrupt JSON file
that then breaks every future read.

That alone doesn't protect a read-modify-write sequence: the touchscreen
UI and device-agent.service's poll loop are separate processes reading
and writing the same file. Wrap load() + mutate + save() in `with
locked(name):` (see pending_actions.py) so the whole sequence is one
critical section - otherwise two processes can each load the same
snapshot, mutate different entries, and the second save() to land wins,
silently discarding the first one's change (lost update).
"""

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_DIR = Path.home() / ".local" / "state" / "device-agent"


@contextmanager
def locked(name: str) -> Iterator[None]:
    """Exclusive file lock for the given store, held for the duration of
    the `with` block. Blocks any other process or thread also calling
    `locked(name)` until this one releases it (including on exception,
    via the `finally`) - each call opens its own file descriptor, so this
    serializes correctly whether the contention is cross-process or
    cross-thread."""
    _DIR.mkdir(parents=True, exist_ok=True)
    lock_path = _DIR / f".{name}.lock"
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load(name: str, default: Any) -> Any:
    path = _DIR / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # Corrupt/truncated file (e.g. power loss mid-write) - don't take
        # the whole approval/rule system down, start fresh instead.
        return default


def save(name: str, data: Any) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    path = _DIR / name
    fd, tmp_path = tempfile.mkstemp(dir=_DIR, prefix=f".{name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2))
        os.replace(tmp_path, path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
