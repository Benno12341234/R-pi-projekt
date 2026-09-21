"""Approval queue for actions the AI wants to take on a connected device.

Approval happens either on the touchscreen (display_ui.py) or via SSH
(cli_approve.py) - both just call resolve(). Once approved, __main__.py
(running only while the USB-C link is up) picks the action up and marks it
executed. Actually acting on the connected host is still not implemented -
see README.md "USB-C Device Agent" for what's open."""

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

_STORE = Path("/var/lib/device-agent/pending_actions.json")


@dataclass
class PendingAction:
    id: str
    description: str
    status: str  # "pending" | "approved" | "denied" | "executed"
    created_at: float


def _load() -> List[dict]:
    if not _STORE.exists():
        return []
    return json.loads(_STORE.read_text())


def _save(actions: List[dict]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(actions, indent=2))


def propose(description: str) -> PendingAction:
    action = PendingAction(
        id=str(uuid.uuid4())[:8],
        description=description,
        status="pending",
        created_at=time.time(),
    )
    actions = _load()
    actions.append(asdict(action))
    _save(actions)
    return action


def list_pending() -> List[PendingAction]:
    return [PendingAction(**a) for a in _load() if a["status"] == "pending"]


def list_approved() -> List[PendingAction]:
    return [PendingAction(**a) for a in _load() if a["status"] == "approved"]


def resolve(action_id: str, approved: bool) -> Optional[PendingAction]:
    actions = _load()
    for a in actions:
        if a["id"] == action_id:
            a["status"] = "approved" if approved else "denied"
            _save(actions)
            return PendingAction(**a)
    return None


def mark_executed(action_id: str) -> None:
    actions = _load()
    for a in actions:
        if a["id"] == action_id:
            a["status"] = "executed"
    _save(actions)
