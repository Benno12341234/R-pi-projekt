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
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

_DIR = Path.home() / ".local" / "state" / "device-agent"


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
